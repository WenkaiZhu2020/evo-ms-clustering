# DayTrader Domain-Informed Proxy Reference

## 1. Purpose and Status

`daytrader_reference_services.csv` is a manually maintained, domain-informed proxy reference partition for the retained DayTrader application classes. It is used to support calibration sanity checks for Stage 1. It is not ground truth, not an official DayTrader decomposition, not independently validated by domain experts.

The mapping records one practical interpretation of DayTrader responsibilities for the 53 retained classes currently analysed by this repository. It should be read as a defensible reference partition for sanity checking, not as proof of the correct microservice architecture.

## 2. Analysis Scope

The mapping covers the DayTrader classes retained after the current subject scope and exclusions in `configs/subjects/daytrader.yml`.

- CSV path: `data/references/daytrader_reference_services.csv`
- Retained mapped classes: 53
- Unique class names: 53
- Unique reference-service labels: 12
- Coverage against the retained DayTrader extracted scope: complete in the current calibration outputs (`53 / 53`)

The subject configuration keeps the application package `com.ibm.websphere.samples.daytrader` and excludes diagnostic or benchmark-support classes such as `web.prims`, `TestServlet`, `TradeBuildDB`, `TradeConfigServlet`, and `TradeScenarioServlet`. Fully qualified class names are used because the extraction pipeline uses fully qualified class names as stable `class_id` values and because simple class names may be ambiguous across packages.

## 3. Construction Principles

The mapping follows practical DDD-inspired grouping rules, but it does not claim that formal DDD workshops, event storming, stakeholder interviews, or independent domain-expert validation were performed.

Rules used:

- group classes around a coherent business capability or primary responsibility;
- keep persistent domain entities separate when they represent focused state such as account, quote, holding, or order;
- group service facades and EJB service implementations around core trading-service behavior;
- distinguish presentation-layer classes from domain entities and service implementations;
- distinguish servlet-based trading entry points from JSF backing beans;
- keep market summary and market streaming separate when class names and packages support that distinction;
- assign technical, utility, configuration, monitoring, and lifecycle classes according to their dominant retained-system responsibility;
- avoid claiming that every technical cluster is a true bounded context.

The labels are therefore reference-service labels for calibration sanity checks, not authoritative bounded-context names.

## 4. Reference-Service Rationale

### `account`

**Business responsibility:**
Account identity and profile state for retained users.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.entities.AccountDataBean`
- `com.ibm.websphere.samples.daytrader.entities.AccountProfileDataBean`

**Rationale:**
The two entity classes represent the account record and its profile details. They belong together because they store identity, login/profile, and user-facing account attributes rather than trade execution or quote data.

**Boundary notes:**
These are persistent entities; account operations that manipulate them live in trading service classes, but the reference cluster keeps the account data model separate.

### `direct_persistence`

**Business responsibility:**
Direct JDBC-style persistence implementation and key-sequence allocation.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.direct.KeySequenceDirect`
- `com.ibm.websphere.samples.daytrader.direct.TradeDirect`

**Rationale:**
`TradeDirect` implements the broad `TradeServices` interface through direct database access, while `KeySequenceDirect` allocates keys for that direct persistence path. They are grouped by persistence mechanism rather than by a single business noun.

**Boundary notes:**
This is a technical implementation cluster. It cuts across trading/account/order/quote capabilities, so the assignment records the dominant persistence responsibility.

### `market_streaming`

**Business responsibility:**
WebSocket message handling and live market-summary update delivery.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.web.websocket.ActionDecoder`
- `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage`
- `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage$1`
- `com.ibm.websphere.samples.daytrader.web.websocket.JsonDecoder`
- `com.ibm.websphere.samples.daytrader.web.websocket.JsonEncoder`
- `com.ibm.websphere.samples.daytrader.web.websocket.JsonMessage`
- `com.ibm.websphere.samples.daytrader.web.websocket.MarketSummaryWebSocket`
- `com.ibm.websphere.samples.daytrader.web.websocket.RecentStockChangeList`

**Rationale:**
The classes are all under `web.websocket` or are the compiled anonymous helper for `ActionMessage`. They encode, decode, represent, and send WebSocket action/JSON messages and recent stock-change summaries.

**Boundary notes:**
`ActionMessage$1` is an inner/generated compiled class retained by class-file extraction; it follows its enclosing `ActionMessage` class.

### `market_summary`

**Business responsibility:**
Market summary calculation, caching, and asynchronous market-summary update handling.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.beans.MarketSummaryDataBean`
- `com.ibm.websphere.samples.daytrader.ejb3.DTStreamer3MDB`
- `com.ibm.websphere.samples.daytrader.ejb3.MarketSummarySingleton`

**Rationale:**
`MarketSummaryDataBean` is the market-summary data object; `MarketSummarySingleton` maintains summary state; `DTStreamer3MDB` handles streaming/update messages related to market summaries.

**Boundary notes:**
This cluster is market-data oriented. It is related to quote data but focuses on aggregate market-summary behavior rather than individual quote persistence.

### `operations_admin`

**Business responsibility:**
Runtime operations and administrative monitoring for the retained application.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.beans.RunStatsDataBean`
- `com.ibm.websphere.samples.daytrader.web.TradeWebContextListener`

**Rationale:**
`RunStatsDataBean` stores run statistics. `TradeWebContextListener` performs web-application lifecycle initialization and shutdown handling. They are grouped as operational support rather than end-user trading behavior.

**Boundary notes:**
This is not a pure business bounded context. It is a practical support/admin cluster for retained operational classes.

### `order`

**Business responsibility:**
Order lifecycle and asynchronous broker processing.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB`
- `com.ibm.websphere.samples.daytrader.entities.OrderDataBean`

**Rationale:**
`OrderDataBean` represents order state. `DTBroker3MDB` processes broker/order messages. They belong together because both are centered on buy/sell order completion and broker-side processing.

**Boundary notes:**
Order actions are invoked by broader trading services and web/UI classes, but the order data and broker message handling form a focused order responsibility.

### `platform_util`

**Business responsibility:**
Shared platform utilities, configuration, logging, timing, and infrastructure support.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.util.CompleteOrderThread`
- `com.ibm.websphere.samples.daytrader.util.FinancialUtils`
- `com.ibm.websphere.samples.daytrader.util.KeyBlock`
- `com.ibm.websphere.samples.daytrader.util.KeyBlock$KeyBlockIterator`
- `com.ibm.websphere.samples.daytrader.util.Log`
- `com.ibm.websphere.samples.daytrader.util.MDBStats`
- `com.ibm.websphere.samples.daytrader.util.TimerStat`
- `com.ibm.websphere.samples.daytrader.util.TradeConfig`
- `com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage`

**Rationale:**
These utility classes provide cross-cutting behavior: order-completion threading, financial formatting/calculation, key-block iteration, logging, message timing/statistics, runtime configuration, and WebSocket/JMS annotation support.

**Boundary notes:**
This is intentionally an infrastructure-oriented cluster. Several classes support multiple business capabilities and do not map naturally to one business service.

### `portfolio`

**Business responsibility:**
User holdings and portfolio position state.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.entities.HoldingDataBean`

**Rationale:**
`HoldingDataBean` represents a user holding, including quantity, quote, purchase price, and purchase date. It is separated from account and order because it models the retained portfolio position.

**Boundary notes:**
Portfolio UI classes are grouped under `web_ui`; this cluster contains the persistent portfolio entity.

### `quote`

**Business responsibility:**
Individual stock quote state.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.entities.QuoteDataBean`

**Rationale:**
`QuoteDataBean` represents quote attributes such as symbol, company name, price, volume, open, low, high, and change. It is the retained persistent quote entity.

**Boundary notes:**
Quote display and JSF wrapper classes are grouped under `web_ui`; market-summary aggregate logic is grouped separately.

### `trading_services`

**Business responsibility:**
Core trading service facade and EJB service implementation.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.TradeAction`
- `com.ibm.websphere.samples.daytrader.TradeServices`
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean`
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean$quotePriceComparator`
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal`
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote`

**Rationale:**
These classes define or implement the main trading API: `TradeServices`, the action/facade implementation, session bean local/remote interfaces, and the session bean implementation. The comparator inner class is retained with its enclosing service implementation.

**Boundary notes:**
The service facade touches accounts, holdings, orders, and quotes; this cluster records the central application-service responsibility rather than a single entity boundary.

### `web_trading`

**Business responsibility:**
Servlet/filter based web trading entry points.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.web.OrdersAlertFilter`
- `com.ibm.websphere.samples.daytrader.web.TradeAppServlet`
- `com.ibm.websphere.samples.daytrader.web.TradeServletAction`

**Rationale:**
`TradeAppServlet` receives servlet requests, `TradeServletAction` dispatches trading actions, and `OrdersAlertFilter` handles order-alert request filtering. They are grouped as non-JSF web trading interface code.

**Boundary notes:**
These classes call into trading services; they are interface/adaptor classes, not independent domain services.

### `web_ui`

**Business responsibility:**
JSF presentation models, producers, validators, and page backing beans.

**Assigned classes:**
- `com.ibm.websphere.samples.daytrader.web.jsf.AccountDataJSF`
- `com.ibm.websphere.samples.daytrader.web.jsf.ExternalContextProducer`
- `com.ibm.websphere.samples.daytrader.web.jsf.HoldingData`
- `com.ibm.websphere.samples.daytrader.web.jsf.JSFLoginFilter`
- `com.ibm.websphere.samples.daytrader.web.jsf.LoginValidator`
- `com.ibm.websphere.samples.daytrader.web.jsf.MarketSummaryJSF`
- `com.ibm.websphere.samples.daytrader.web.jsf.OrderData`
- `com.ibm.websphere.samples.daytrader.web.jsf.OrderDataJSF`
- `com.ibm.websphere.samples.daytrader.web.jsf.PortfolioJSF`
- `com.ibm.websphere.samples.daytrader.web.jsf.QuoteData`
- `com.ibm.websphere.samples.daytrader.web.jsf.QuoteJSF`
- `com.ibm.websphere.samples.daytrader.web.jsf.TradeActionProducer`
- `com.ibm.websphere.samples.daytrader.web.jsf.TradeAppJSF`
- `com.ibm.websphere.samples.daytrader.web.jsf.TradeConfigJSF`

**Rationale:**
The assigned classes are JSF-facing backing/data/producer/filter/validator/configuration classes for account, holdings, orders, portfolio, quote, market summary, login, and application pages. They belong together because their primary responsibility is web presentation and request/session interaction.

**Boundary notes:**
This cluster contains many business nouns because JSF backing classes mirror UI screens. Their placement is presentation-layer oriented rather than domain-boundary oriented.

## 5. Ambiguous and Cross-Cutting Classes

Several retained classes are technical or cross-cutting rather than clean business-domain classes:

- `platform_util` contains logging, configuration, timing/statistics, key-block iteration, financial helpers, completion-thread support, and WebSocket/JMS support. These classes support multiple business capabilities.
- `direct_persistence` implements a direct persistence path for the broad `TradeServices` interface, so it cuts across several business operations.
- `operations_admin` groups runtime statistics and web lifecycle support. These classes are operational support, not user-facing trading capabilities.
- `web_ui` groups JSF backing and presentation classes. Many of those classes mention accounts, orders, holdings, portfolio, quotes, or market summaries, but their dominant responsibility is presentation and request/session interaction.
- `market_streaming` includes retained inner/generated class `ActionMessage$1`, which follows the enclosing `ActionMessage` responsibility because extraction operates over compiled class files.
- `trading_services` is broad because the DayTrader service facade coordinates several trading operations. It is retained as the core application-service cluster rather than split by every entity it touches.

The mapping records one practical interpretation. Other decompositions could reasonably place some infrastructure or presentation classes differently.

## 6. Intended Use

The proxy reference is used for:

- reference coverage checks;
- `mojofm_vs_reference`;
- pairwise precision, recall, and F1;
- ARI and NMI against the proxy partition;
- secondary calibration sanity checks.

It is not used as:

- an optimization objective;
- the primary formal profile-selection criterion;
- proof of the correct microservice architecture;
- an independently validated external benchmark.

DayTrader calibration is constrained internal-primary. Internal structural metrics guide profile selection, and reference metrics remain secondary sanity checks.

## 7. Limitations

- The mapping is manually constructed and manually maintained.
- No independent domain-expert validation is recorded in the repository.
- It is based on the retained static-analysis scope, not the full original DayTrader source tree.
- Technical classes do not always map naturally to business capabilities or bounded contexts.
- Presentation classes and infrastructure classes may have multiple plausible placements.
- Other valid decompositions may exist.
- Results against this proxy reference must be interpreted cautiously.
