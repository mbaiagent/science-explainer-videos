title: 登录认证：Session、JWT 与 OAuth2，服务器怎么「记住」你
subtitle: HTTP 无状态与 Cookie、Session 与分布式会话共享、JWT 三段结构与签名校验、令牌失效与 refresh token 轮换、OAuth2 授权码 + PKCE、OAuth2 与 OIDC 的区别、Cookie 属性与 CSRF/XSS 防护、密码哈希存储，附五段可运行的 Python 演示
tag: 计算机与后端
color: #fda4af

![登录成功后，下一个请求服务器却不认识你](img/f-6.4.jpg)

## 先说问题：HTTP 不记得你

![Cookie：服务器下发、浏览器保存并自动携带](img/f-17.jpg)

你在登录页输入账号密码，服务器校验通过，返回「登录成功」。接着你点开「我的订单」，浏览器发出第二个请求——服务器怎么知道这个请求也是你发的？

答案是：**HTTP 本身不知道**。HTTP 是一个**无状态**协议，每个请求都是独立的，服务器处理完就忘，协议层面没有「这个请求和上一个请求来自同一个人」的概念。无状态让服务器实现简单、容易横向扩展，但「登录」这件事天然需要状态：服务器得记住「你已经证明过自己是谁了」。

所有登录方案要解决的都是同一个问题：**让后续请求带上一个凭证，服务器看到凭证就知道是谁**。区别只在于凭证是什么、放在哪、怎么验证。

> 先分清两个词：**认证**（Authentication）回答「你是谁」，比如账号密码登录；**授权**（Authorization）回答「你能做什么」，比如「这个应用可以读你的相册，但不能发帖」。后面讲 OAuth2 和 OIDC 时，这个区别非常关键。

### Cookie：浏览器替你保管的小纸条

Cookie 是 HTTP 的一个扩展机制（RFC 6265），流程只有两步：

1. 服务器在响应里加一个 `Set-Cookie` 头，比如 `Set-Cookie: sid=a1b2c3; HttpOnly; Secure; SameSite=Lax`；
2. 浏览器把它存下来，之后**每次访问同一站点，自动在请求头里带上** `Cookie: sid=a1b2c3`。

几个要点：

| 属性 | 作用 |
|---|---|
| `Domain` / `Path` | 作用范围：哪些域名、哪些路径下的请求会携带它 |
| `Expires` / `Max-Age` | 过期时间；都不设就是「会话 Cookie」，通常关闭浏览器后失效 |
| `HttpOnly` | JavaScript 读不到（`document.cookie` 里看不见），降低被 XSS 偷走的风险 |
| `Secure` | 只在 HTTPS 连接中发送 |
| `SameSite` | 限制跨站请求是否携带：`Strict` / `Lax` / `None` |

RFC 6265 要求浏览器至少支持单个 Cookie 4096 字节、每个域名 50 个 Cookie，所以 Cookie 适合放**小而关键**的东西。

Cookie 本身只是一个「携带工具」。里面放的东西决定了方案：放一个**随机编号**，服务器拿编号去查用户信息，这就是 **Session**；放一张**自带用户信息和签名的令牌**，服务器验签即可，这就是 **Token**（典型是 JWT）。

## Session：状态存在服务端

![Session 存在服务端；多实例部署时用 Redis 集中存放](img/f-29.4.jpg)

### 工作原理

1. 用户登录成功，服务器生成一个**随机且不可预测**的 sessionId，在服务端存一条记录：`sessionId → { userId: 42, role: "user", ... }`；
2. 通过 `Set-Cookie` 把 sessionId 发给浏览器；
3. 之后每个请求带着 Cookie 过来，服务器用 sessionId 查到会话数据，就知道是谁了。

Java 的 Servlet 容器（如 Tomcat）默认用名为 `JSESSIONID` 的 Cookie，PHP 默认是 `PHPSESSID`，原理都一样。

浏览器手里只有一个毫无意义的随机串，所有用户数据都在服务器上。这带来两个好处：**数据不出服务器**，以及**随时可以作废**——退出登录、修改密码、封号，删掉服务端的那条记录，下一个请求就立即失效。

### sessionId 的要求

- **足够随机**：必须用密码学安全的随机数生成器，长度足够（OWASP 建议至少 64 位熵），不能用自增 ID 或时间戳，否则可以被猜出来；
- **登录后更换**：如果登录前就有 sessionId，登录成功后要换一个新的。否则攻击者可以先把一个自己知道的 sessionId 塞给受害者，等受害者登录后直接冒用，这叫**会话固定攻击**（Session Fixation）；
- **设置过期**：通常用「滑动过期」，比如 30 分钟无操作就失效；关键系统再加一个绝对过期时间。

### 分布式下的问题：Session 存在哪？

单机时 Session 放在进程内存里就行。但服务一旦部署多个实例，负载均衡把请求分到不同的机器上：在实例 A 上登录，下一个请求打到实例 B，B 的内存里没有这条会话，用户就被「踢」回了登录页。

| 方案 | 做法 | 问题 |
|---|---|---|
| 粘性会话 | 负载均衡按 Cookie 或 IP 把同一用户固定到同一实例 | 实例宕机或扩缩容时会话丢失，负载可能不均 |
| 会话复制 | 实例之间互相同步 Session | 实例多了以后同步开销大，基本不再使用 |
| **集中存储** | 所有实例都从 **Redis** 读写 Session | 多一次网络调用；Redis 要做高可用 |

主流做法是**集中存储到 Redis**：sessionId 作为 key，会话数据作为 value，过期时间直接用 Redis 的 TTL。Java 生态里，Spring Session 可以几乎无侵入地把 `HttpSession` 换成 Redis 存储（参考写法，需要 Redis 环境，本文未运行）：

```java
// 依赖：spring-boot-starter-data-redis + spring-session-data-redis
@Configuration
@EnableRedisHttpSession(maxInactiveIntervalInSeconds = 1800)
public class SessionConfig { }

// 业务代码不用改，照常使用 HttpSession，数据实际存到了 Redis
@PostMapping("/login")
public String login(HttpServletRequest req, @RequestBody LoginForm form) {
    User u = userService.check(form.username(), form.password());
    req.changeSessionId();                       // 登录后更换 sessionId，防会话固定
    req.getSession().setAttribute("userId", u.id());
    return "ok";
}
```

Session 的代价也很清楚：**每个请求都要查一次存储**。对大多数业务这完全可以接受（Redis 一次查询通常在毫秒以内），但如果有大量服务都需要验证用户身份，都去访问同一个 Session 存储，就会形成耦合。这正是 Token 方案想解决的问题。

## Token 与 JWT：把信息写进令牌，再签个名

![JWT 的三段结构：Header、Payload、Signature](img/f-41.jpg)

Token 方案的思路是：**不在服务端存会话**，而是把「你是谁、什么时候过期」直接写进令牌里交给客户端，再用签名保证它不能被伪造。服务器收到令牌后，只要验证签名有效、没过期，就可以信任里面的内容。

最常用的令牌格式是 **JWT**（JSON Web Token，RFC 7519），读作 "jot"。

### 三段结构

一个 JWT 长这样（为了便于阅读这里换了行，实际是一整行）：

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
.eyJzdWIiOiI0MiIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzYwMDAwMDAwLCJleHAiOjE3NjAwMDA5MDB9
.XzSDshbH0WW9Z8Nud0Nf2ne3O6RQ1qp0w4qNzcLJqbg
```

用 `.` 分成三段，每段都是 **Base64URL 编码**（把 Base64 的 `+/` 换成 `-_`，并去掉末尾的 `=`）：

| 段 | 解码后 | 作用 |
|---|---|---|
| Header | `{"alg":"HS256","typ":"JWT"}` | 声明签名算法 |
| Payload | `{"sub":"42","role":"user","iat":1760000000,"exp":1760000900}` | 声明（claims）：用户是谁、何时签发、何时过期 |
| Signature | 32 字节的 HMAC 结果 | `HMAC-SHA256(header + "." + payload, 服务端密钥)` |

RFC 7519 定义了几个**注册声明**：`iss`（签发者）、`sub`（主体，通常是用户 ID）、`aud`（接收方）、`exp`（过期时间）、`nbf`（生效时间）、`iat`（签发时间）、`jti`（令牌唯一 ID）。时间都是 Unix 秒数。

### 签名不是加密

这是关于 JWT 最常见的误解。Header 和 Payload **只是编码，不是加密**，任何人拿到 token 都能解码看到内容——下面的实验里，不用密钥一行代码就能还原 payload。

签名保证的是两件事：

- **完整性**：内容没被改过。改了 payload 中任何一个字符，重新计算出的签名就对不上；
- **来源可信**：只有持有密钥的一方才能生成有效签名。

所以 **payload 里不要放密码、手机号、身份证号等敏感信息**。如果确实需要加密，要用 JWE（RFC 7516），但实践中很少这样做。严格来说，带签名的 JWT 是一个 JWS（JSON Web Signature，RFC 7515）。

### 对称签名 vs 非对称签名

| 算法 | 密钥 | 适合 |
|---|---|---|
| **HS256**（HMAC-SHA256） | 签发和验证用**同一个密钥** | 签发方和验证方是同一个服务 |
| **RS256 / ES256**（RSA / ECDSA） | 私钥签发，**公钥**验证 | 一个认证中心签发，多个服务验证 |

在微服务里，常见做法是认证服务用私钥签发，其他服务从一个公开地址（JWKS，JSON Web Key Set）拿到公钥来验证。这样各个服务都能独立验证 token，却没有一个能伪造 token。

### 无状态的好处

验证 JWT 只需要密钥（或公钥）和当前时间，**不需要查任何存储**：

- 任何实例、任何服务拿到 token 都能直接验证，天然适合多实例和微服务；
- 也适合跨域、移动端、服务间调用等不方便使用 Cookie 的场景，通常放在请求头 `Authorization: Bearer <token>` 里。

## 无状态的代价：发出去的令牌收不回来

![JWT 难以主动失效：短期 access token + refresh token，或黑名单](img/f-53.jpg)

JWT 的优点和缺点是同一件事：**服务端不存状态**。这意味着一旦签发，在 `exp` 之前它**一直有效**。用户点了「退出登录」、改了密码、账号被封，服务器都没有办法让已经发出去的 token 失效——它根本不记得自己发过哪些 token。

### 方案一：短期 access token + refresh token

最主流的做法是把令牌拆成两种：

| | access token | refresh token |
|---|---|---|
| 有效期 | **短**，常见几分钟到一小时 | **长**，几天到几十天 |
| 用途 | 每个 API 请求都带上 | 只用来换新的 access token |
| 校验 | 无状态，只验签名和 exp | **服务端存储并检查**，可随时吊销 |
| 发给谁 | 资源服务器 | 只发给认证服务器 |

这样，「无状态」只保留在高频的 API 调用上，「可吊销」的检查放在低频的刷新动作上。用户被封号后，最多再撑一个 access token 的有效期（比如 15 分钟），之后刷新时就会被拒绝。

refresh token 本身更值钱，需要额外保护：

- **轮换**（rotation）：每次刷新都发一个新的 refresh token，旧的立即作废；
- **重用检测**：如果一个已经用过的 refresh token 又被拿来刷新，说明它很可能被偷了。此时把这一整条刷新链全部吊销，让用户重新登录。这是 OAuth 2.0 安全最佳实践（RFC 9700）中推荐的做法之一。

后面的实验三会实现这套逻辑。

### 方案二：黑名单

退出登录时，把这个 token 的 `jti`（或者整个 token 的哈希）写进 Redis，过期时间设为 token 的剩余有效期；验签通过后，再查一次黑名单。

这确实能做到立即失效，但每个请求又要查一次 Redis——**又引入了状态**，某种程度上回到了 Session 的老路。实践中黑名单一般和短期 access token 搭配：只有少量「需要立刻踢下线」的 token 进黑名单，而且黑名单里的记录很快就会过期。

### 另一种思路：令牌版本号

在用户表里存一个 `token_version`，签发 token 时写进 payload。改密码或「退出所有设备」时把版本号加 1，校验时比较两者。这同样需要查一次用户数据（可以缓存），好处是一次操作就能让该用户的所有 token 失效。

### Session 和 JWT 怎么选

| | Session | JWT |
|---|---|---|
| 状态存在 | 服务端（内存 / Redis） | 客户端（令牌本身） |
| 每次请求 | 查一次存储 | 只验签名 |
| 主动失效 | 删记录，立即生效 | 难，需要短期令牌、黑名单等配合 |
| 体积 | Cookie 里只有一个短 ID | 令牌较大，每个请求都带着 |
| 适合 | 传统 Web 应用、单体或少量服务 | 微服务、移动端、跨域、服务间调用 |

很多人默认「JWT 更先进」，其实不然。**对于普通的网站，Session + Redis 往往更简单、更安全**：失效可控、Cookie 有成熟的安全属性。JWT 的真正价值在于**跨服务、跨组织地传递身份**，比如下面要讲的 OAuth2 和 OIDC。

## OAuth2：第三方登录到底授权了什么

![OAuth2 授权码 + PKCE 流程](img/f-65.3.jpg)

你在某个应用上点「用 GitHub 账号登录」，或者授权一个工具读取你的网盘文件。这时有一个问题：**这个应用需要访问你在另一个平台上的数据，但你不应该把那个平台的密码交给它**。

OAuth 2.0（RFC 6749）就是为此设计的**授权框架**。它有四个角色：

| 角色 | 例子 |
|---|---|
| 资源所有者（Resource Owner） | 你，也就是用户 |
| 客户端（Client） | 想访问你数据的应用 |
| 授权服务器（Authorization Server） | 平台负责登录和发令牌的服务 |
| 资源服务器（Resource Server） | 平台存着你数据的 API |

### 授权码流程（Authorization Code）+ PKCE

这是目前推荐的流程，不论是有后端的 Web 应用、单页应用还是手机 App 都适用：

1. **用户点击「用第三方账号登录」**；
2. 应用把浏览器**重定向到授权服务器**，URL 中带上：`client_id`（应用是谁）、`redirect_uri`（授权后跳回哪里）、`scope`（要什么权限）、`state`（随机值，防 CSRF）、`code_challenge`（PKCE，见下文）；
3. 用户**在授权服务器的页面上**登录，并看到「某应用想要读取你的公开信息和邮箱」，点击同意。**密码只交给了授权服务器**；
4. 授权服务器把浏览器重定向回 `redirect_uri?code=xxx&state=yyy`。应用检查 `state` 和自己发出去的一致；
5. 应用的后端拿着 `code` + `code_verifier`（机密客户端还要带 `client_secret`）向授权服务器的令牌端点**换取令牌**。这一步是服务器之间的直接调用，不经过浏览器；
6. 授权服务器返回 `access_token`（可能还有 `refresh_token`）；
7. 应用带着 `Authorization: Bearer <access_token>` 调用资源服务器的 API。

为什么要先发一个 `code` 再换 token，而不是直接把 token 放在重定向 URL 里？因为浏览器的 URL 会出现在历史记录、日志、Referer 头里，容易泄露。授权码**短期有效**（RFC 6749 建议最长 10 分钟）且**只能使用一次**，真正的令牌通过后端直接获取。早期直接在 URL 里返回 token 的「隐式模式」（Implicit）已经不再推荐。

### PKCE：截获了授权码也没用

授权码在第 4 步要经过浏览器，在手机上还可能经过系统的 URL 跳转，存在被恶意应用截获的可能。**PKCE**（Proof Key for Code Exchange，RFC 7636，读作 "pixy"）的做法是：

1. 客户端随机生成一个 `code_verifier`，自己留着；
2. 计算 `code_challenge = BASE64URL(SHA256(code_verifier))`，放在第 2 步的授权请求里；
3. 第 5 步换令牌时，必须提交原始的 `code_verifier`，授权服务器算一下哈希，和当初的 `code_challenge` 比对。

攻击者即使截获了 `code`，也不知道 `code_verifier`（它从没离开过客户端），就换不到令牌。PKCE 最初是为手机 App 这类无法安全保存 `client_secret` 的「公开客户端」设计的，现在的安全最佳实践（RFC 9700）建议所有客户端都使用。

### scope：令牌能做什么

`scope` 限定 access token 的权限范围，比如 `read:user`、`repo`。资源服务器在处理请求时要检查 token 的 scope 是否覆盖当前操作。按**最小权限**原则申请 scope，用户也更愿意授权。

### 其他授权方式

| 授权方式 | 场景 |
|---|---|
| 授权码 + PKCE | 有用户参与的登录和授权，**首选** |
| 客户端凭证（Client Credentials） | 服务和服务之间调用，没有用户参与 |
| 设备码（Device Code，RFC 8628） | 电视、命令行工具等不方便输入的设备 |
| 刷新令牌（Refresh Token） | 用 refresh token 换新的 access token |
| ~~密码模式~~、~~隐式模式~~ | 已不推荐使用 |

### OAuth2 vs OIDC：授权 vs 认证

OAuth2 是**授权**协议：它回答「这个应用能不能读取你的相册」。access token 是给**资源服务器**看的通行证，对客户端来说，它应该被当作一串不透明的字符串，客户端不应该解析它，更不应该把它当作「用户是谁」的证明。

但「用第三方账号登录」要的恰恰是**认证**：应用想知道「现在登录的是谁」。拿 access token 去调用户信息接口来推断身份，存在被「换 token」攻击的风险：攻击者把从别的应用拿到的、属于受害者的 access token 塞给你的应用，你的应用无法分辨这个 token 是不是发给自己的。

**OIDC**（OpenID Connect）在 OAuth2 之上补上了认证这一层：

- 授权请求的 `scope` 里加上 `openid`；
- 令牌端点除了 access token，还会返回一个 **id_token**，它是一个 JWT，专门给**客户端**看的「身份证明」；
- id_token 里有：`iss`（谁签发的）、`sub`（用户在该平台的唯一 ID）、`aud`（**发给哪个客户端**，必须等于自己的 client_id）、`exp`、`iat`，以及防重放的 `nonce` 等；
- 客户端必须验证 id_token 的签名（用授权服务器公布的公钥）、`iss`、`aud`、`exp` 和 `nonce`。

| | OAuth2 | OIDC |
|---|---|---|
| 解决的问题 | 授权：应用能做什么 | 认证：用户是谁 |
| 核心产物 | access_token | **id_token**（JWT）+ access_token |
| 给谁看 | 资源服务器 | 客户端 |
| 额外的东西 | — | UserInfo 接口、发现文档 `/.well-known/openid-configuration` |

并不是所有平台都实现了 OIDC。比如 GitHub 的 OAuth App 登录，就是拿 access token 调用户信息接口（`/user`）获取身份。接入这类平台时，要确保 token 确实是通过自己发起的授权码流程拿到的，不能接受从外部直接传进来的 access token。

## 安全底线

![OAuth2 与 OIDC 的区别，以及 Cookie、CSRF、XSS、密码存储的安全要点](img/f-77.3.jpg)

不管用哪种方案，下面这些都不能省。

### Cookie 的三个属性

```text
Set-Cookie: sid=...; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=1800
```

- **HttpOnly**：页面脚本读不到这个 Cookie，XSS 就无法直接把它偷走；
- **Secure**：只通过 HTTPS 发送，避免在明文网络中泄露；
- **SameSite**：从其他网站发起的请求是否携带 Cookie。`Strict` 完全不带；`Lax` 只在用户点击链接这类顶层 GET 跳转时携带，跨站的 POST、iframe、图片请求都不带；`None` 表示总是携带，此时必须同时设置 `Secure`。Chrome 等浏览器对没有声明 SameSite 的 Cookie 默认按 `Lax` 处理。

### CSRF：借你的 Cookie 发请求

跨站请求伪造（CSRF）：你登录了银行网站，又打开了一个恶意网页，恶意网页里藏着一个自动提交的表单，目标是银行的转账接口。浏览器发送请求时**自动带上了银行的 Cookie**，银行以为是你本人操作。

CSRF 的根源是「Cookie 自动携带」。防护手段：

- **SameSite=Lax 或 Strict**：跨站的 POST 请求不再携带 Cookie，挡住了大部分 CSRF；
- **CSRF Token**：服务端在表单或页面里放一个随机值，提交时校验。恶意网站读不到这个值，也就伪造不了请求；
- **校验 Origin / Referer 头**，或者现代浏览器提供的 `Sec-Fetch-Site` 头；
- **会修改数据的操作不要用 GET**，因为 `Lax` 对顶层 GET 跳转是放行的。

用 `Authorization: Bearer` 头传 token 的接口天然不受 CSRF 影响，因为浏览器不会自动添加这个头。

### XSS：注入脚本，什么都能做

跨站脚本（XSS）：攻击者设法让自己的脚本在你的页面上运行，比如在评论区里提交了一段没被转义的 `<script>`。脚本运行在你的域名下，可以读取 `localStorage`、调用接口、修改页面。

- **防护的根本**是输出时正确转义、不拼接 HTML，配合 **CSP**（内容安全策略）限制可以执行的脚本来源；
- 如果 token 放在 `localStorage`，XSS 可以直接把它发到攻击者的服务器，之后在任何地方使用；放在 HttpOnly Cookie 里，脚本读不到，但**仍然可以在页面内以你的身份发请求**。HttpOnly 能减少损失，但不能代替修复 XSS 本身；
- 对于浏览器里的单页应用，一种越来越常见的做法是 **BFF**（Backend for Frontend）：由同域的后端完成 OAuth 流程、保管令牌，浏览器和 BFF 之间只用 HttpOnly 的 Session Cookie。

### 密码：用慢哈希，加盐

**永远不要存明文密码，也不要用 MD5、SHA-256 直接哈希**。通用哈希被设计得非常快，一张显卡每秒可以尝试数十亿次，泄露的哈希库很快就会被暴力破解出大部分弱密码。

应该使用专门的**密码哈希算法**，它们故意设计得很慢，还可以调节成本：

| 算法 | 说明 |
|---|---|
| **Argon2id** | 密码哈希竞赛（PHC）的胜出算法，同时消耗内存和 CPU，OWASP 首选 |
| **scrypt** | 也是内存困难型，Python 标准库 `hashlib.scrypt` 即可使用 |
| **bcrypt** | 久经考验，各语言都有成熟实现；注意输入超过 72 字节的部分会被忽略 |
| PBKDF2 | 有 FIPS 认证要求时使用，需要很高的迭代次数 |

每个密码都要使用独立的随机**盐**，这样相同的密码哈希结果不同，彩虹表就失效了。成熟的库（如 Spring Security 的 `BCryptPasswordEncoder`、Python 的 `argon2-cffi`）会自动处理盐，并把算法参数和盐一起存进结果字符串。实验四用标准库的 scrypt 演示这一点。

### 其他

- **全站 HTTPS**：Cookie、token、密码在明文网络中都是「裸奔」（见本系列《HTTPS》）；
- **登录接口限流**、连续失败后加验证码或临时锁定，防止撞库和暴力破解（见本系列《限流算法》）；
- 登录失败时统一提示「账号或密码错误」，不要透露账号是否存在；
- 敏感操作（改密码、转账）要求重新验证身份。

## 动手实验

下面的代码都只依赖 Python 标准库（实验一最后的交叉验证用了 PyJWT），在 Python 3.13 下运行。

### 实验一：手写 HS256 JWT 的签发与校验

```python
import base64, hashlib, hmac, json, time

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def sign(payload: dict, key: bytes) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(key, f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url_encode(sig)}"

class InvalidToken(Exception):
    pass

def verify(token: str, key: bytes, now: float | None = None, leeway: int = 0) -> dict:
    try:
        h, p, s = token.split(".")
    except ValueError:
        raise InvalidToken("格式错误：应为三段")
    header = json.loads(b64url_decode(h))
    if header.get("alg") != "HS256":                 # 只接受服务端预期的算法，拒绝 none 等
        raise InvalidToken(f"不接受的算法：{header.get('alg')}")
    expected = hmac.new(key, f"{h}.{p}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, b64url_decode(s)):   # 常量时间比较
        raise InvalidToken("签名不匹配")
    payload = json.loads(b64url_decode(p))
    now = time.time() if now is None else now
    if "exp" in payload and now > payload["exp"] + leeway:
        raise InvalidToken("已过期")
    return payload

KEY = b"server-side-secret-at-least-32-bytes!!"

if __name__ == "__main__":
    iat = 1_760_000_000                                  # 为了输出可复现，固定「现在」的时间
    token = sign({"sub": "42", "role": "user", "iat": iat, "exp": iat + 900}, KEY)
    print("token:", token)

    # 1. 签名不是加密：不需要密钥就能看到 payload
    print("\n[1] 不用密钥直接解码 payload:", b64url_decode(token.split(".")[1]).decode())

    # 2. 正常校验
    print("[2] 校验通过:", verify(token, KEY, now=iat + 60))

    def try_verify(label, tok, key=KEY, now=iat + 60):
        try:
            verify(tok, key, now=now); print(f"[{label}] 竟然通过了！")
        except InvalidToken as e:
            print(f"[{label}] 拒绝：{e}")

    # 3. 篡改 payload：把 role 改成 admin，签名保持原样
    h, p, s = token.split(".")
    evil = json.loads(b64url_decode(p)); evil["role"] = "admin"
    forged = f"{h}.{b64url_encode(json.dumps(evil, separators=(',', ':')).encode())}.{s}"
    try_verify("3 篡改 payload", forged)

    # 4. 用错误的密钥自己重新签一个
    try_verify("4 攻击者自签", sign({**evil, "exp": iat + 900}, b"guessed-key"))

    # 5. alg=none 攻击：去掉签名、声明不签名
    none_h = b64url_encode(b'{"alg":"none","typ":"JWT"}')
    try_verify("5 alg=none", f"{none_h}.{p}.")

    # 6. 过期判断（exp = iat + 900 秒）
    try_verify("6 15 分钟后", token, now=iat + 901)
    print("[7] 允许 30 秒时钟偏差时:", "通过" if verify(token, KEY, now=iat + 901, leeway=30) else "")
```

输出：

```text
token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MiIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzYwMDAwMDAwLCJleHAiOjE3NjAwMDA5MDB9.XzSDshbH0WW9Z8Nud0Nf2ne3O6RQ1qp0w4qNzcLJqbg

[1] 不用密钥直接解码 payload: {"sub":"42","role":"user","iat":1760000000,"exp":1760000900}
[2] 校验通过: {'sub': '42', 'role': 'user', 'iat': 1760000000, 'exp': 1760000900}
[3 篡改 payload] 拒绝：签名不匹配
[4 攻击者自签] 拒绝：签名不匹配
[5 alg=none] 拒绝：不接受的算法：none
[6 15 分钟后] 拒绝：已过期
[7] 允许 30 秒时钟偏差时: 通过
```

几个值得注意的细节：

- **签名比较用 `hmac.compare_digest`**：普通的 `==` 在第一个不同的字节就返回，耗时会泄露「前面有几个字节是对的」，理论上可以被用来逐字节猜签名（计时攻击）；
- **算法由服务端决定，而不是读 token 里的 `alg`**：历史上一些 JWT 库会「听 token 的话」，接受 `alg: none`（不签名），或者在本该用 RS256 公钥验证时被诱导用 HS256，把公开的公钥当成 HMAC 密钥，导致任何人都能伪造 token。RFC 8725（JWT 最佳实践）要求验证方明确限定允许的算法；
- **HS256 的密钥至少 256 位**（RFC 7518 的要求），而且必须是随机生成的，不能是 `secret`、`123456` 这种可以离线暴力猜解的字符串；
- `leeway` 用来容忍服务器之间几秒到几十秒的时钟偏差。

用成熟的库 PyJWT 做交叉验证，手写实现生成的 token 与库生成的逐字节相同：

```python
import jwt                      # PyJWT，只用来交叉验证我们手写的实现
from jwt_hs256 import sign, KEY
iat = 1_760_000_000
mine = sign({"sub": "42", "role": "user", "iat": iat, "exp": iat + 900}, KEY)
lib = jwt.encode({"sub": "42", "role": "user", "iat": iat, "exp": iat + 900}, KEY, algorithm="HS256")
print("与 PyJWT 生成的完全一致:", mine == lib)
print("PyJWT 校验手写的 token:", jwt.decode(mine, KEY, algorithms=["HS256"], options={"verify_exp": False}))
```

```text
与 PyJWT 生成的完全一致: True
PyJWT 校验手写的 token: {'sub': '42', 'role': 'user', 'iat': 1760000000, 'exp': 1760000900}
```

> 生产环境请使用成熟的库，并且像上面一样**显式传入 `algorithms=["HS256"]`**。手写只是为了看清原理。

### 实验二：一个最小的 Session 登录

用标准库起一个 HTTP 服务，`http.cookiejar` 扮演浏览器保存 Cookie：

```python
import http.cookiejar, json, secrets, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie

SESSIONS = {}            # sessionId -> {"user": ..., "expires": ...}；生产环境放 Redis
TTL = 30 * 60            # 30 分钟无操作过期（滑动过期）
USERS = {"alice": "correct-horse"}   # 仅演示；真实系统存的是密码哈希

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):        # 关掉默认访问日志
        pass

    def current_session(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        sid = cookie["sid"].value if "sid" in cookie else None
        s = SESSIONS.get(sid)
        if not s or s["expires"] < time.time():
            SESSIONS.pop(sid, None)
            return None, None
        s["expires"] = time.time() + TTL                  # 每次访问续期
        return sid, s

    def reply(self, code, body, set_cookie=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def do_POST(self):
        form = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/login":
            if USERS.get(form["user"]) != form["password"]:
                return self.reply(401, {"error": "账号或密码错误"})
            old_sid, _ = self.current_session()
            SESSIONS.pop(old_sid, None)                     # 登录后换新 sessionId，防会话固定
            sid = secrets.token_urlsafe(32)                 # 不可预测的随机编号
            SESSIONS[sid] = {"user": form["user"], "expires": time.time() + TTL}
            # 本地演示走 http，所以没加 Secure；线上必须加
            return self.reply(200, {"ok": True}, f"sid={sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age={TTL}")
        if self.path == "/logout":
            sid, _ = self.current_session()
            SESSIONS.pop(sid, None)                         # 服务端删除，立即失效
            return self.reply(200, {"ok": True}, "sid=; Max-Age=0; Path=/")

    def do_GET(self):
        sid, s = self.current_session()
        if self.path == "/me":
            if not s:
                return self.reply(401, {"error": "未登录"})
            return self.reply(200, {"user": s["user"]})

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}"

jar = http.cookiejar.CookieJar()                           # 扮演浏览器保存 Cookie
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def call(method, path, body=None):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with opener.open(req) as r:
            return r.status, json.loads(r.read()), r.headers.get("Set-Cookie")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), None

print("1. 未登录访问 /me      ->", call("GET", "/me")[:2])
code, body, sc = call("POST", "/login", {"user": "alice", "password": "correct-horse"})
print("2. 登录                ->", code, body)
print("   Set-Cookie:", sc.split("=", 1)[0] + "=<43 位随机串>;" + sc.split(";", 1)[1])
print("   浏览器保存的 Cookie:", [c.name for c in jar])
print("3. 再访问 /me          ->", call("GET", "/me")[:2])
print("   服务端会话数:", len(SESSIONS), "；sid 长度:", len(next(iter(SESSIONS))))
print("4. 退出登录            ->", call("POST", "/logout", {})[:2])
print("5. 退出后访问 /me      ->", call("GET", "/me")[:2], "；服务端会话数:", len(SESSIONS))
server.shutdown()
```

输出：

```text
1. 未登录访问 /me      -> (401, {'error': '未登录'})
2. 登录                -> 200 {'ok': True}
   Set-Cookie: sid=<43 位随机串>; HttpOnly; SameSite=Lax; Path=/; Max-Age=1800
   浏览器保存的 Cookie: ['sid']
3. 再访问 /me          -> (200, {'user': 'alice'})
   服务端会话数: 1 ；sid 长度: 43
4. 退出登录            -> (200, {'ok': True})
5. 退出后访问 /me      -> (401, {'error': '未登录'}) ；服务端会话数: 0
```

第 3 步里客户端代码没有手动处理任何 Cookie，是 CookieJar 自动带上的，这就是浏览器的行为。第 5 步展示了 Session 最大的优势：**服务端删掉记录，立即失效**。把 `SESSIONS` 这个字典换成 Redis 的 `SET sid value EX 1800` 和 `GET sid`，就是分布式 Session 的雏形。

### 实验三：refresh token 轮换与重用检测

复用实验一的 `sign` / `verify`：

```python
import hashlib, secrets
from jwt_hs256 import sign, verify, KEY, InvalidToken

ACCESS_TTL = 15 * 60
REFRESH = {}   # sha256(refresh_token) -> {"user", "family", "used"}；生产环境放数据库 / Redis
REVOKED_FAMILIES = set()

def h(tok): return hashlib.sha256(tok.encode()).hexdigest()   # 只存哈希，库泄露也拿不到原值

def issue(user, family, now):
    access = sign({"sub": user, "iat": now, "exp": now + ACCESS_TTL}, KEY)
    refresh = secrets.token_urlsafe(32)
    REFRESH[h(refresh)] = {"user": user, "family": family, "used": False}
    return access, refresh

def login(user, now):
    return issue(user, family=secrets.token_hex(4), now=now)

def refresh(token, now):
    rec = REFRESH.get(h(token))
    if rec is None or rec["family"] in REVOKED_FAMILIES:
        raise InvalidToken("refresh token 无效或已吊销")
    if rec["used"]:                                  # 旧 token 被再次使用 → 很可能泄露了
        REVOKED_FAMILIES.add(rec["family"])          # 整个家族全部作废，强制重新登录
        raise InvalidToken("检测到 refresh token 被重复使用，已吊销整个会话")
    rec["used"] = True                               # 轮换：每个 refresh token 只能用一次
    return issue(rec["user"], rec["family"], now)

t0 = 1_760_000_000
a1, r1 = login("42", t0)
print("登录后 access 有效:", verify(a1, KEY, now=t0 + 60)["sub"])
try:
    verify(a1, KEY, now=t0 + 16 * 60)
except InvalidToken as e:
    print("16 分钟后 access:", e)
a2, r2 = refresh(r1, t0 + 16 * 60)
print("用 r1 换到新的 access:", verify(a2, KEY, now=t0 + 17 * 60)["sub"], "| r1 与 r2 不同:", r1 != r2)

# 攻击者此前偷到了 r1，现在拿来用
try:
    refresh(r1, t0 + 20 * 60)
except InvalidToken as e:
    print("攻击者重放 r1:", e)
# 连带着，合法用户手里的 r2 也失效了
try:
    refresh(r2, t0 + 31 * 60)
except InvalidToken as e:
    print("合法用户用 r2:", e)
```

输出：

```text
登录后 access 有效: 42
16 分钟后 access: 已过期
用 r1 换到新的 access: 42 | r1 与 r2 不同: True
攻击者重放 r1: 检测到 refresh token 被重复使用，已吊销整个会话
合法用户用 r2: refresh token 无效或已吊销
```

服务端分不清谁是攻击者、谁是合法用户，所以选择「全部作废、重新登录」，宁可让用户多登录一次。真实系统中，用户主动退出或修改密码时，也是把对应的 family 加入吊销列表。

### 实验四：密码加盐慢哈希

```python
import hashlib, hmac, os, time

# scrypt 参数取 OWASP 密码存储备忘单给出的最低配置：N=2^17, r=8, p=1（约 128 MiB 内存）
N, R, P = 2**17, 8, 1

def hash_password(password: str) -> str:
    salt = os.urandom(16)                                  # 每个密码独立的随机盐
    dk = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, maxmem=256 * 1024 * 1024, dklen=32)
    return f"scrypt${N}${R}${P}${salt.hex()}${dk.hex()}"   # 参数、盐和结果一起存

def check_password(password: str, stored: str) -> bool:
    _, n, r, p, salt, dk = stored.split("$")
    got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                         maxmem=256 * 1024 * 1024, dklen=32)
    return hmac.compare_digest(got.hex(), dk)

h1, h2 = hash_password("123456"), hash_password("123456")
print("同一个密码，两次结果不同（盐不同）:")
print(" ", h1[:60] + "...")
print(" ", h2[:60] + "...")
print("正确密码:", check_password("123456", h1), " 错误密码:", check_password("1234567", h1))

t = time.perf_counter(); check_password("123456", h1); slow = time.perf_counter() - t
t = time.perf_counter()
for _ in range(10000): hashlib.sha256(b"123456").digest()
fast = (time.perf_counter() - t) / 10000
print(f"scrypt 一次约 {slow*1000:.0f} ms；SHA-256 一次约 {fast*1e6:.2f} µs，相差约 {slow/fast:,.0f} 倍")
```

输出（盐是随机的，耗时取决于机器）：

```text
同一个密码，两次结果不同（盐不同）:
  scrypt$131072$8$1$88483d4d5be142fe44281a7d1e90b6a8$33f941d89...
  scrypt$131072$8$1$cbf19719554d2fa736784f039bbb1c09$eab9878ea...
正确密码: True  错误密码: False
scrypt 一次约 590 ms；SHA-256 一次约 0.45 µs，相差约 1,320,989 倍
```

对正常用户来说，登录时多等几百毫秒感觉不到；但对拿着泄露哈希库暴力破解的攻击者来说，每次尝试都慢了上百万倍，还要占用大量内存，显卡并行的优势也被大幅削弱。实际项目中参数要根据服务器能力和登录 QPS 来调。

### 实验五：PKCE 的 code_challenge

```python
import base64, hashlib, secrets

def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def make_pkce():
    verifier = b64url(secrets.token_bytes(32))              # 43 个字符，只留在客户端
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge

v, c = make_pkce()
print("code_verifier  (留在客户端):", v)
print("code_challenge (放进授权请求):", c)

# 授权服务器在用 code 换令牌时校验：SHA256(verifier) 是否等于当初的 challenge
check = lambda verifier, challenge: b64url(hashlib.sha256(verifier.encode()).digest()) == challenge
print("持有 verifier 的客户端:", check(v, c))
print("只截获了 code 的攻击者:", check(make_pkce()[0], c))

# RFC 7636 附录 B 的官方测试向量
rv = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
print("RFC 7636 测试向量:", b64url(hashlib.sha256(rv.encode()).digest()))
```

输出（前两行每次运行不同）：

```text
code_verifier  (留在客户端): BLd-srwStA6IDONzaIJyWh_KfUzQhCcTObZfA_25tuE
code_challenge (放进授权请求): GsFcPKIBI0KVDVN_KB2wCfx-frzibLlMD44s7brBRQ8
持有 verifier 的客户端: True
只截获了 code 的攻击者: False
RFC 7636 测试向量: E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
```

最后一行与 RFC 7636 附录 B 中给出的结果 `E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM` 一致。SHA-256 是单向的，攻击者看到 `code_challenge` 也反推不出 `code_verifier`。

## 工程实践与常见坑

- **别自己发明协议**：密码哈希、JWT、OAuth2 都用成熟的库和框架（如 Spring Security、各语言的 OIDC 客户端库），自己写的只用于理解原理；
- **JWT 不是越大越好**：只放必要的声明（用户 ID、过期时间、少量角色），权限变化频繁的数据别放进去，否则改了权限要等 token 过期才生效；
- **校验要完整**：签名、算法白名单、`exp`、`iss`、`aud` 一个都不能少。只验签名不验 `aud`，别的系统签给别人的 token 也能用在你这里；
- **注意时钟**：多台服务器之间时钟不一致会导致刚签发的 token 被判「未生效」或「已过期」，用 NTP 同步，并留几十秒的 leeway；
- **密钥要能轮换**：在 Header 里带上 `kid`（密钥 ID），新旧密钥并存一段时间，再下线旧密钥；
- **OAuth2 的 redirect_uri 要精确匹配**：授权服务器只接受预先注册的完整地址，模糊匹配曾导致授权码被重定向到攻击者的域名；
- **`state` 和 `nonce` 都要校验**：`state` 防止授权回调被 CSRF，`nonce` 防止 id_token 被重放；
- **退出登录要做全**：Session 方案删除服务端记录；JWT 方案吊销 refresh token，必要时把 access token 加入黑名单；接了 OIDC 的还要考虑是否同时退出授权服务器（单点登出）；
- **日志里别打印 token 和 Cookie**：它们就是用户的「钥匙」。

## 高频面试题速答

**Q：Cookie 和 Session 有什么区别？**
Cookie 是存在浏览器、每次请求自动携带的数据；Session 是存在服务端的会话数据。常见组合是 Cookie 里只放 sessionId，服务器用它查 Session。

**Q：分布式环境下 Session 怎么共享？**
主流做法是把 Session 集中存储在 Redis 里（如 Spring Session），所有实例都从 Redis 读写；也可以用粘性会话，但实例故障时会话会丢失。

**Q：JWT 由哪几部分组成？安全吗？**
Header、Payload、Signature 三段，各自 Base64URL 编码后用「.」连接。签名保证不被篡改，但 Payload 不加密，任何人都能解码，所以不能放敏感信息。

**Q：JWT 如何实现退出登录 / 主动失效？**
JWT 本身无法撤回。常用做法：短期 access token + 可吊销的 refresh token；退出时把 jti 加入 Redis 黑名单（TTL 为剩余有效期）；或在用户表维护 token 版本号。

**Q：Session 和 JWT 怎么选？**
需要随时踢人下线、单体或少量服务的 Web 应用，Session + Redis 更简单；微服务、移动端、跨域或跨组织传递身份时，JWT 更合适。

**Q：OAuth2 授权码模式的流程是什么？为什么需要授权码？**
重定向到授权服务器 → 用户登录并同意 → 带 code 跳回 → 后端用 code（+ PKCE verifier / client_secret）换 access token → 调 API。授权码短期一次性，真正的 token 通过后端直连获取，不暴露在浏览器 URL 中。

**Q：PKCE 解决什么问题？**
防止授权码被截获后被换成令牌。客户端发送 code_verifier 的哈希，换令牌时提交原值，只有发起请求的客户端才知道原值。

**Q：OAuth2 和 OIDC 的区别？**
OAuth2 是授权协议，产物是给资源服务器用的 access token；OIDC 在 OAuth2 之上加了认证，额外返回 id_token（JWT），告诉客户端「谁登录了」。

**Q：CSRF 和 XSS 有什么区别，怎么防？**
CSRF 是借用户的 Cookie 从其他网站发请求，防护用 SameSite、CSRF Token、校验 Origin；XSS 是在页面里注入脚本，防护用输出转义和 CSP，HttpOnly 可以防止 Cookie 被脚本读取。

**Q：密码应该怎么存？**
用 Argon2id、scrypt 或 bcrypt 这类慢哈希算法，每个密码独立加盐，不能存明文，也不能只做一次 MD5 / SHA-256。

## 总结

![四个关键概念](img/f-83.jpg)

- HTTP 是**无状态**的，登录方案的本质都是「让后续请求带上凭证」；
- **Cookie** 是浏览器自动携带的小纸条，配合 `HttpOnly`、`Secure`、`SameSite` 使用；
- **Session**：状态存在服务端，Cookie 里只放随机的 sessionId；多实例用 **Redis** 集中存储；可以随时作废；
- **JWT**：Header.Payload.Signature，**签名不是加密**；无状态、易扩展，但难以主动失效，靠**短期 access token + 可吊销、会轮换的 refresh token** 弥补；
- **OAuth2** 是授权：授权码 + **PKCE**，应用拿不到用户密码，只拿到限定 scope 的 access token；**OIDC** 在其上加了认证，用 **id_token** 告诉客户端「谁登录了」；
- 安全底线：全站 HTTPS、防 CSRF 与 XSS、密码用 Argon2id / scrypt / bcrypt 加盐存储、校验时限定算法。

<div class="refs" markdown="1">

### 参考资料

- RFC 6265：HTTP State Management Mechanism（Cookie）.
- RFC 7519：JSON Web Token (JWT)；RFC 7515：JSON Web Signature (JWS)；RFC 7516：JSON Web Encryption (JWE)；RFC 7518：JSON Web Algorithms (JWA).
- RFC 8725：JSON Web Token Best Current Practices.
- RFC 6749：The OAuth 2.0 Authorization Framework；RFC 6750：Bearer Token Usage.
- RFC 7636：Proof Key for Code Exchange by OAuth Public Clients (PKCE).
- RFC 9700：Best Current Practice for OAuth 2.0 Security.
- RFC 8628：OAuth 2.0 Device Authorization Grant.
- OpenID Connect Core 1.0（OpenID Foundation）.
- OWASP Cheat Sheet Series：Session Management、Password Storage、Cross-Site Request Forgery Prevention、JSON Web Token for Java.
- Spring Session 文档：Spring Session with Redis.
- Python 文档：hmac、hashlib、secrets、http.cookies、http.cookiejar.

</div>
