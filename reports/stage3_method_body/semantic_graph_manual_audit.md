# Stage 3B semantic graph manual audit

Fixed sample: first five sorted classes; five lowest neighbour retention; five highest non-trivial retention; all body-truncated classes; first five empty-body classes; all Xerces collision-group members; and five highest Stage 3B degree classes. Classes are listed once.

## jpetstore

### `org.mybatis.jpetstore.domain.Account` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: org.mybatis.jpetstore.domain.Order; org.mybatis.jpetstore.domain.Category; org.mybatis.jpetstore.domain.Product
Stage 3B neighbours: org.mybatis.jpetstore.domain.Order [w=0.576682823937, G_raw=true]; org.mybatis.jpetstore.service.AccountService [w=0.556163778757, G_raw=true]; org.mybatis.jpetstore.domain.Category [w=0.551198096531, G_raw=false]

### `org.mybatis.jpetstore.domain.Cart` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: org.mybatis.jpetstore.domain.CartItem; org.mybatis.jpetstore.domain.Order; org.mybatis.jpetstore.domain.Item
Stage 3B neighbours: org.mybatis.jpetstore.domain.CartItem [w=0.739198140384, G_raw=true]; org.mybatis.jpetstore.web.actions.CartActionBean [w=0.621796032871, G_raw=true]; org.mybatis.jpetstore.domain.Order [w=0.597130584848, G_raw=true]

### `org.mybatis.jpetstore.domain.CartItem` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.mybatis.jpetstore.domain.Cart; org.mybatis.jpetstore.domain.LineItem; org.mybatis.jpetstore.domain.Item
Stage 3B neighbours: org.mybatis.jpetstore.domain.LineItem [w=0.772370689391, G_raw=true]; org.mybatis.jpetstore.domain.Cart [w=0.739198140384, G_raw=true]; org.mybatis.jpetstore.domain.Item [w=0.619841438163, G_raw=true]

### `org.mybatis.jpetstore.domain.Category` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=4
Stage 3A neighbours: org.mybatis.jpetstore.domain.Product; org.mybatis.jpetstore.domain.Account; org.mybatis.jpetstore.domain.Item
Stage 3B neighbours: org.mybatis.jpetstore.domain.Product [w=0.827444057894, G_raw=false]; org.mybatis.jpetstore.domain.Account [w=0.551198096531, G_raw=false]; org.mybatis.jpetstore.mapper.CategoryMapper [w=0.548050555326, G_raw=true]

### `org.mybatis.jpetstore.domain.Item` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.mybatis.jpetstore.domain.LineItem; org.mybatis.jpetstore.domain.CartItem; org.mybatis.jpetstore.domain.Product
Stage 3B neighbours: org.mybatis.jpetstore.domain.LineItem [w=0.645248462889, G_raw=true]; org.mybatis.jpetstore.domain.Product [w=0.624294230732, G_raw=true]; org.mybatis.jpetstore.domain.CartItem [w=0.619841438163, G_raw=true]

### `org.mybatis.jpetstore.domain.Order` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=4
Stage 3A neighbours: org.mybatis.jpetstore.domain.LineItem; org.mybatis.jpetstore.domain.Cart; org.mybatis.jpetstore.domain.Item
Stage 3B neighbours: org.mybatis.jpetstore.domain.LineItem [w=0.682148254314, G_raw=true]; org.mybatis.jpetstore.service.OrderService [w=0.598916233522, G_raw=true]; org.mybatis.jpetstore.domain.Cart [w=0.597130584848, G_raw=true]

### `org.mybatis.jpetstore.domain.Product` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: org.mybatis.jpetstore.domain.Category; org.mybatis.jpetstore.domain.Item; org.mybatis.jpetstore.domain.CartItem
Stage 3B neighbours: org.mybatis.jpetstore.domain.Category [w=0.827444057894, G_raw=false]; org.mybatis.jpetstore.domain.Item [w=0.624294230732, G_raw=true]; org.mybatis.jpetstore.mapper.ProductMapper [w=0.5409925971, G_raw=true]

### `org.mybatis.jpetstore.mapper.AccountMapper` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.mybatis.jpetstore.mapper.OrderMapper; org.mybatis.jpetstore.service.AccountService; org.mybatis.jpetstore.mapper.CategoryMapper
Stage 3B neighbours: org.mybatis.jpetstore.service.AccountService [w=0.780783613441, G_raw=true]; org.mybatis.jpetstore.mapper.OrderMapper [w=0.761322477113, G_raw=false]; org.mybatis.jpetstore.mapper.CategoryMapper [w=0.645457380086, G_raw=false]

### `org.mybatis.jpetstore.mapper.CategoryMapper` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=0.6666666666666666; degree=7
Stage 3A neighbours: org.mybatis.jpetstore.mapper.ProductMapper; org.mybatis.jpetstore.mapper.OrderMapper; org.mybatis.jpetstore.mapper.LineItemMapper
Stage 3B neighbours: org.mybatis.jpetstore.mapper.ProductMapper [w=0.783828129246, G_raw=false]; org.mybatis.jpetstore.mapper.OrderMapper [w=0.680721122014, G_raw=false]; org.mybatis.jpetstore.mapper.AccountMapper [w=0.645457380086, G_raw=false]

### `org.mybatis.jpetstore.mapper.ItemMapper` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.mybatis.jpetstore.mapper.ProductMapper; org.mybatis.jpetstore.mapper.LineItemMapper; org.mybatis.jpetstore.mapper.CategoryMapper
Stage 3B neighbours: org.mybatis.jpetstore.mapper.ProductMapper [w=0.71668655649, G_raw=false]; org.mybatis.jpetstore.mapper.LineItemMapper [w=0.710014949822, G_raw=false]; org.mybatis.jpetstore.mapper.CategoryMapper [w=0.642348880506, G_raw=false]

### `org.mybatis.jpetstore.mapper.LineItemMapper` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: org.mybatis.jpetstore.mapper.OrderMapper; org.mybatis.jpetstore.mapper.ItemMapper; org.mybatis.jpetstore.mapper.CategoryMapper
Stage 3B neighbours: org.mybatis.jpetstore.mapper.OrderMapper [w=0.72779170848, G_raw=false]; org.mybatis.jpetstore.mapper.ItemMapper [w=0.710014949822, G_raw=false]; org.mybatis.jpetstore.mapper.ProductMapper [w=0.625759511342, G_raw=false]

### `org.mybatis.jpetstore.mapper.OrderMapper` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=0.6666666666666666; degree=7
Stage 3A neighbours: org.mybatis.jpetstore.mapper.AccountMapper; org.mybatis.jpetstore.service.OrderService; org.mybatis.jpetstore.mapper.LineItemMapper
Stage 3B neighbours: org.mybatis.jpetstore.mapper.AccountMapper [w=0.761322477113, G_raw=false]; org.mybatis.jpetstore.mapper.LineItemMapper [w=0.72779170848, G_raw=false]; org.mybatis.jpetstore.mapper.CategoryMapper [w=0.680721122014, G_raw=false]

### `org.mybatis.jpetstore.mapper.ProductMapper` — highest_stage3b_degree
body_empty=true; body_tokens_truncated=0; retention=1.0; degree=6
Stage 3A neighbours: org.mybatis.jpetstore.mapper.CategoryMapper; org.mybatis.jpetstore.mapper.ItemMapper; org.mybatis.jpetstore.mapper.OrderMapper
Stage 3B neighbours: org.mybatis.jpetstore.mapper.CategoryMapper [w=0.783828129246, G_raw=false]; org.mybatis.jpetstore.mapper.ItemMapper [w=0.71668655649, G_raw=false]; org.mybatis.jpetstore.mapper.OrderMapper [w=0.676503551783, G_raw=false]

### `org.mybatis.jpetstore.web.actions.CartActionBean` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=5
Stage 3A neighbours: org.mybatis.jpetstore.web.actions.CatalogActionBean; org.mybatis.jpetstore.web.actions.OrderActionBean; org.mybatis.jpetstore.web.actions.AccountActionBean
Stage 3B neighbours: org.mybatis.jpetstore.web.actions.CatalogActionBean [w=0.745335011545, G_raw=false]; org.mybatis.jpetstore.web.actions.OrderActionBean [w=0.705069592078, G_raw=true]; org.mybatis.jpetstore.web.actions.AccountActionBean [w=0.640603477628, G_raw=false]

## daytrader

### `com.ibm.websphere.samples.daytrader.TradeAction` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=8
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.TradeServices; com.ibm.websphere.samples.daytrader.direct.TradeDirect; com.ibm.websphere.samples.daytrader.web.TradeServletAction
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.direct.TradeDirect [w=0.778207092941, G_raw=true]; com.ibm.websphere.samples.daytrader.TradeServices [w=0.769698817529, G_raw=true]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean [w=0.729461139056, G_raw=true]

### `com.ibm.websphere.samples.daytrader.TradeServices` — first_sorted
body_empty=true; body_tokens_truncated=0; retention=0.6666666666666666; degree=4
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.TradeAction; com.ibm.websphere.samples.daytrader.direct.TradeDirect; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.TradeAction [w=0.769698817529, G_raw=true]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote [w=0.706698271196, G_raw=true]; com.ibm.websphere.samples.daytrader.direct.TradeDirect [w=0.691273456878, G_raw=true]

### `com.ibm.websphere.samples.daytrader.beans.MarketSummaryDataBean` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=7
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.web.jsf.MarketSummaryJSF; com.ibm.websphere.samples.daytrader.ejb3.MarketSummarySingleton; com.ibm.websphere.samples.daytrader.beans.RunStatsDataBean
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.web.jsf.MarketSummaryJSF [w=0.769164451789, G_raw=true]; com.ibm.websphere.samples.daytrader.ejb3.MarketSummarySingleton [w=0.672817703495, G_raw=true]; com.ibm.websphere.samples.daytrader.entities.QuoteDataBean [w=0.622150492751, G_raw=true]

### `com.ibm.websphere.samples.daytrader.beans.RunStatsDataBean` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=5
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.beans.MarketSummaryDataBean; com.ibm.websphere.samples.daytrader.entities.OrderDataBean; com.ibm.websphere.samples.daytrader.entities.AccountDataBean
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.entities.OrderDataBean [w=0.629817531369, G_raw=false]; com.ibm.websphere.samples.daytrader.beans.MarketSummaryDataBean [w=0.600211165219, G_raw=false]; com.ibm.websphere.samples.daytrader.entities.QuoteDataBean [w=0.550374510357, G_raw=false]

### `com.ibm.websphere.samples.daytrader.direct.KeySequenceDirect` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.util.KeyBlock; com.ibm.websphere.samples.daytrader.util.KeyBlock$KeyBlockIterator; com.ibm.websphere.samples.daytrader.direct.TradeDirect
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.util.KeyBlock [w=0.540704283733, G_raw=true]; com.ibm.websphere.samples.daytrader.util.KeyBlock$KeyBlockIterator [w=0.493681661032, G_raw=false]; com.ibm.websphere.samples.daytrader.direct.TradeDirect [w=0.448787331852, G_raw=true]

### `com.ibm.websphere.samples.daytrader.util.CompleteOrderThread` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.0; degree=3
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.web.jsf.OrderData; com.ibm.websphere.samples.daytrader.web.OrdersAlertFilter; com.ibm.websphere.samples.daytrader.TradeAction
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.web.jsf.OrderDataJSF [w=0.493548690654, G_raw=false]; com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB [w=0.477128358838, G_raw=false]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean [w=0.473751646844, G_raw=true]

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean$quotePriceComparator` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.3333333333333333; degree=3
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.entities.QuoteDataBean [w=0.494245402397, G_raw=true]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean [w=0.482739746829, G_raw=true]; com.ibm.websphere.samples.daytrader.web.jsf.QuoteData [w=0.473821382675, G_raw=false]

### `com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage` — lowest_retention
body_empty=true; body_tokens_truncated=0; retention=0.3333333333333333; degree=3
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.web.websocket.MarketSummaryWebSocket; com.ibm.websphere.samples.daytrader.ejb3.DTStreamer3MDB; com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.web.websocket.MarketSummaryWebSocket [w=0.465166925691, G_raw=false]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote [w=0.428863580201, G_raw=false]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal [w=0.417322661722, G_raw=false]

### `com.ibm.websphere.samples.daytrader.web.TradeWebContextListener` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.3333333333333333; degree=4
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.web.TradeAppServlet; com.ibm.websphere.samples.daytrader.web.OrdersAlertFilter; com.ibm.websphere.samples.daytrader.web.TradeServletAction
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.web.TradeAppServlet [w=0.556118177941, G_raw=false]; com.ibm.websphere.samples.daytrader.TradeAction [w=0.531802442748, G_raw=false]; com.ibm.websphere.samples.daytrader.util.TradeConfig [w=0.530993149341, G_raw=true]

### `com.ibm.websphere.samples.daytrader.web.jsf.ExternalContextProducer` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.3333333333333333; degree=3
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.web.jsf.TradeActionProducer; com.ibm.websphere.samples.daytrader.web.TradeWebContextListener; com.ibm.websphere.samples.daytrader.web.jsf.LoginValidator
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.web.jsf.TradeActionProducer [w=0.520236089674, G_raw=false]; com.ibm.websphere.samples.daytrader.web.jsf.OrderDataJSF [w=0.426569158383, G_raw=false]; com.ibm.websphere.samples.daytrader.web.jsf.QuoteJSF [w=0.398289294701, G_raw=false]

### `com.ibm.websphere.samples.daytrader.ejb3.DTStreamer3MDB` — highest_nontrivial_retention
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean; com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB [w=0.841691491797, G_raw=false]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean [w=0.446308048534, G_raw=false]; com.ibm.websphere.samples.daytrader.util.MDBStats [w=0.433147857613, G_raw=true]

### `com.ibm.websphere.samples.daytrader.direct.TradeDirect` — body_truncated
body_empty=false; body_tokens_truncated=31; retention=1.0; degree=6
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.TradeAction; com.ibm.websphere.samples.daytrader.TradeServices; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.TradeAction [w=0.778207092941, G_raw=true]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean [w=0.709433926659, G_raw=true]; com.ibm.websphere.samples.daytrader.TradeServices [w=0.691273456878, G_raw=true]

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean; com.ibm.websphere.samples.daytrader.TradeServices
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote [w=0.856409370758, G_raw=false]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean [w=0.699510067652, G_raw=true]; com.ibm.websphere.samples.daytrader.TradeServices [w=0.678968214462, G_raw=true]

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean; com.ibm.websphere.samples.daytrader.TradeServices
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal [w=0.856409370758, G_raw=false]; com.ibm.websphere.samples.daytrader.TradeServices [w=0.706698271196, G_raw=true]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean [w=0.677590089058, G_raw=true]

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=8
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote; com.ibm.websphere.samples.daytrader.direct.TradeDirect
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.TradeAction [w=0.729461139056, G_raw=true]; com.ibm.websphere.samples.daytrader.direct.TradeDirect [w=0.709433926659, G_raw=true]; com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal [w=0.699510067652, G_raw=true]

### `com.ibm.websphere.samples.daytrader.web.jsf.OrderDataJSF` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=7
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.web.jsf.AccountDataJSF; com.ibm.websphere.samples.daytrader.web.jsf.QuoteJSF; com.ibm.websphere.samples.daytrader.entities.OrderDataBean
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.web.jsf.AccountDataJSF [w=0.721673620143, G_raw=false]; com.ibm.websphere.samples.daytrader.entities.OrderDataBean [w=0.680961183921, G_raw=true]; com.ibm.websphere.samples.daytrader.web.jsf.QuoteJSF [w=0.66221640235, G_raw=false]

### `com.ibm.websphere.samples.daytrader.web.jsf.QuoteData` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=0.3333333333333333; degree=7
Stage 3A neighbours: com.ibm.websphere.samples.daytrader.entities.QuoteDataBean; com.ibm.websphere.samples.daytrader.web.jsf.OrderData; com.ibm.websphere.samples.daytrader.web.jsf.HoldingData
Stage 3B neighbours: com.ibm.websphere.samples.daytrader.entities.QuoteDataBean [w=0.771232368153, G_raw=false]; com.ibm.websphere.samples.daytrader.web.jsf.QuoteJSF [w=0.620142475253, G_raw=true]; com.ibm.websphere.samples.daytrader.beans.MarketSummaryDataBean [w=0.606417322772, G_raw=false]

## xerces

### `org.apache.xerces.dom.ASDOMImplementationImpl` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom3.as.DOMImplementationAS; org.apache.xerces.dom.DOMImplementationImpl; org.apache.xerces.parsers.DOMASBuilderImpl
Stage 3B neighbours: org.apache.xerces.dom3.as.DOMImplementationAS [w=0.834036071993, G_raw=true]; org.apache.xerces.dom.DOMImplementationImpl [w=0.694842010587, G_raw=true]; org.apache.xerces.parsers.DOMASBuilderImpl [w=0.693216144106, G_raw=true]

### `org.apache.xerces.dom.ASModelImpl` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=4
Stage 3A neighbours: org.apache.xerces.dom3.as.ASModel; org.apache.xerces.dom3.as.DocumentAS; org.apache.xerces.dom3.as.ASObject
Stage 3B neighbours: org.apache.xerces.dom3.as.ASModel [w=0.856184100061, G_raw=true]; org.apache.xerces.dom3.as.DOMImplementationAS [w=0.732473009057, G_raw=false]; org.apache.xerces.dom3.as.DocumentAS [w=0.721660001699, G_raw=false]

### `org.apache.xerces.dom.AttrImpl` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.xs.opti.AttrImpl; org.apache.xerces.dom.AttrNSImpl; org.apache.xerces.dom.ElementImpl
Stage 3B neighbours: org.apache.xerces.impl.xs.opti.AttrImpl [w=0.84736752636, G_raw=false]; org.apache.xerces.dom.AttrNSImpl [w=0.772978512108, G_raw=true]; org.apache.xerces.dom.ElementImpl [w=0.711656401238, G_raw=false]

### `org.apache.xerces.dom.AttrNSImpl` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=4
Stage 3A neighbours: org.apache.xerces.dom.ElementNSImpl; org.apache.xerces.stax.events.NamespaceImpl; org.apache.xerces.impl.xs.opti.AttrImpl
Stage 3B neighbours: org.apache.xerces.dom.ElementNSImpl [w=0.832312829235, G_raw=false]; org.apache.xerces.stax.events.NamespaceImpl [w=0.797409879662, G_raw=false]; org.apache.xerces.dom.AttrImpl [w=0.772978512108, G_raw=true]

### `org.apache.xerces.dom.AttributeMap` — first_sorted
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: org.apache.xerces.impl.xs.opti.NamedNodeMapImpl; org.apache.xerces.dom.NamedNodeMapImpl; org.apache.xerces.impl.xs.util.XSNamedMapImpl
Stage 3B neighbours: org.apache.xerces.dom.NamedNodeMapImpl [w=0.767157562568, G_raw=true]; org.apache.xerces.impl.xs.opti.NamedNodeMapImpl [w=0.754310382072, G_raw=false]; org.apache.xerces.dom.AttrImpl [w=0.668855720619, G_raw=true]

### `org.apache.xerces.dom.LCount` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.0; degree=3
Stage 3A neighbours: org.apache.xerces.util.SymbolHash; org.apache.xerces.impl.xs.traversers.LargeContainer; org.apache.xerces.impl.xs.traversers.Container
Stage 3B neighbours: org.apache.xerces.dom.DeferredDocumentImpl$RefCount [w=0.50623144677, G_raw=false]; org.apache.xerces.parsers.XMLGrammarPreparser$XMLGrammarLoaderContainer [w=0.473662872966, G_raw=false]; org.apache.xerces.impl.xs.XSConstraints$1 [w=0.468970499838, G_raw=false]

### `org.apache.xerces.impl.XMLEntityManager$1` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$4 [w=0.625861982289, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$4 [w=0.625861982289, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$4 [w=0.625861982289, G_raw=false]

### `org.apache.xerces.impl.dtd.XMLDTDLoader` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.0; degree=5
Stage 3A neighbours: org.apache.xerces.xni.grammars.XMLGrammarLoader; org.apache.xerces.parsers.DTDParser; org.apache.xerces.impl.dtd.XML11DTDProcessor
Stage 3B neighbours: org.apache.xerces.impl.xs.XMLSchemaLoader [w=0.749317934414, G_raw=false]; org.apache.xerces.impl.dtd.XMLDTDProcessor [w=0.736231524518, G_raw=true]; org.apache.xerces.impl.XMLDTDScannerImpl [w=0.728785165994, G_raw=true]

### `org.apache.xerces.impl.dv.xs.TypeValidator$1` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1
Stage 3B neighbours: org.apache.xerces.impl.dv.xs.TypeValidator [w=0.731416063198, G_raw=true]; org.apache.xerces.impl.dv.dtd.StringDatatypeValidator [w=0.571372857884, G_raw=false]; org.apache.xerces.impl.dv.xs.XSSimpleTypeDecl$1 [w=0.564292527265, G_raw=false]

### `org.apache.xerces.impl.xpath.regex.Token$StringToken` — lowest_retention
body_empty=false; body_tokens_truncated=0; retention=0.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.xpath.regex.Token$CharToken; org.apache.xerces.impl.xpath.regex.Token; org.apache.xerces.impl.xpath.regex.Token$ConcatToken
Stage 3B neighbours: org.apache.xerces.impl.xpath.regex.Op$StringOp [w=0.634829798566, G_raw=false]; org.apache.xerces.impl.xpath.regex.Token$UnionToken [w=0.605108598038, G_raw=false]; org.apache.xerces.impl.xpath.regex.Token$ParenToken [w=0.605045414337, G_raw=false]

### `org.apache.xerces.dom.CDATASectionImpl` — highest_nontrivial_retention
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: org.apache.xerces.dom.DeferredCDATASectionImpl; org.apache.xerces.dom.CommentImpl; org.apache.xerces.dom.TextImpl
Stage 3B neighbours: org.apache.xerces.dom.CommentImpl [w=0.703749383395, G_raw=false]; org.apache.xerces.dom.DeferredCDATASectionImpl [w=0.680813847003, G_raw=true]; org.apache.xerces.dom.CharacterDataImpl [w=0.559149193589, G_raw=false]

### `org.apache.xerces.dom.CharacterDataImpl` — highest_nontrivial_retention
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=5
Stage 3A neighbours: org.apache.xerces.dom.TextImpl; org.apache.xerces.dom.CommentImpl; org.apache.xerces.dom3.as.CharacterDataEditAS
Stage 3B neighbours: org.apache.xerces.dom.TextImpl [w=0.702881158028, G_raw=true]; org.apache.xerces.dom3.as.CharacterDataEditAS [w=0.670575036321, G_raw=false]; org.apache.xerces.impl.xs.opti.DefaultText [w=0.665739256305, G_raw=false]

### `org.apache.xerces.dom.CoreDocumentImpl` — body_truncated
body_empty=false; body_tokens_truncated=1; retention=0.3333333333333333; degree=9
Stage 3A neighbours: org.apache.xerces.dom.DocumentImpl; org.apache.xerces.dom.DocumentTypeImpl; org.apache.xerces.impl.xs.opti.DefaultDocument
Stage 3B neighbours: org.apache.xerces.dom.DocumentImpl [w=0.807564007768, G_raw=true]; org.apache.xerces.dom.CoreDOMImplementationImpl [w=0.71517266638, G_raw=true]; org.apache.xerces.dom.DeferredDocumentImpl [w=0.71390809102, G_raw=false]

### `org.apache.xerces.impl.dv.xs.XSSimpleTypeDecl` — body_truncated
body_empty=false; body_tokens_truncated=342; retention=1.0; degree=7
Stage 3A neighbours: org.apache.xerces.impl.dv.XSSimpleType; org.apache.xerces.xs.XSSimpleTypeDefinition; org.apache.xerces.impl.dv.xs.XSSimpleTypeDelegate
Stage 3B neighbours: org.apache.xerces.impl.dv.xs.XSSimpleTypeDelegate [w=0.77910220726, G_raw=false]; org.apache.xerces.impl.dv.XSSimpleType [w=0.771341968277, G_raw=true]; org.apache.xerces.xs.XSSimpleTypeDefinition [w=0.721207518779, G_raw=true]

### `org.apache.xerces.impl.xpath.regex.Token` — body_truncated
body_empty=false; body_tokens_truncated=44; retention=0.6666666666666666; degree=6
Stage 3A neighbours: org.apache.xerces.impl.xpath.regex.RangeToken; org.apache.xerces.impl.xpath.regex.Token$UnionToken; org.apache.xerces.impl.xpath.regex.Token$ClosureToken
Stage 3B neighbours: org.apache.xerces.impl.xpath.regex.RangeToken [w=0.720833793136, G_raw=true]; org.apache.xerces.impl.xpath.regex.Token$UnionToken [w=0.660674523592, G_raw=true]; org.apache.xerces.impl.xpath.regex.Token$CharToken [w=0.651522441936, G_raw=true]

### `org.apache.xerces.impl.xs.XMLSchemaValidator` — body_truncated
body_empty=false; body_tokens_truncated=125; retention=1.0; degree=6
Stage 3A neighbours: org.apache.xerces.impl.dtd.XMLDTDValidator; org.apache.xerces.impl.xs.traversers.XSDHandler; org.apache.xerces.jaxp.validation.ValidatorHandlerImpl
Stage 3B neighbours: org.apache.xerces.impl.dtd.XMLDTDValidator [w=0.771808206356, G_raw=false]; org.apache.xerces.jaxp.validation.ValidatorHandlerImpl [w=0.725527495615, G_raw=true]; org.apache.xerces.impl.xs.traversers.XSDHandler [w=0.692779129562, G_raw=false]

### `org.apache.xerces.impl.xs.traversers.XSDHandler` — body_truncated
body_empty=false; body_tokens_truncated=134; retention=0.6666666666666666; degree=8
Stage 3A neighbours: org.apache.xerces.impl.xs.SchemaGrammar; org.apache.xerces.impl.xs.XMLSchemaValidator; org.apache.xerces.impl.xs.traversers.SchemaContentHandler
Stage 3B neighbours: org.apache.xerces.impl.xs.SchemaGrammar [w=0.754470386033, G_raw=true]; org.apache.xerces.impl.xs.XMLSchemaValidator [w=0.692779129562, G_raw=false]; org.apache.xerces.impl.xs.XMLSchemaLoader [w=0.692616331078, G_raw=true]

### `org.apache.xerces.util.EncodingMap` — body_truncated
body_empty=false; body_tokens_truncated=34; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xml.serialize.Encodings; org.apache.xml.serialize.EncodingInfo; org.apache.xerces.impl.XMLEntityManager$EncodingInfo
Stage 3B neighbours: org.apache.xml.serialize.EncodingInfo [w=0.655197369914, G_raw=true]; org.apache.xml.serialize.Encodings [w=0.612028352537, G_raw=true]; org.apache.xerces.impl.XMLEntityManager$EncodingInfo [w=0.49763860623, G_raw=false]

### `org.apache.xerces.xinclude.XIncludeHandler` — body_truncated
body_empty=false; body_tokens_truncated=73; retention=0.3333333333333333; degree=3
Stage 3A neighbours: org.apache.xerces.xpointer.XPointerHandler; org.apache.xerces.impl.xs.traversers.XSDHandler; org.apache.xerces.impl.dtd.XMLDTDProcessor
Stage 3B neighbours: org.apache.xerces.parsers.XIncludeParserConfiguration [w=0.702067128325, G_raw=true]; org.apache.xerces.xpointer.XPointerHandler [w=0.699554454806, G_raw=true]; org.apache.xerces.xinclude.XIncludeTextReader [w=0.685755047658, G_raw=true]

### `org.apache.xerces.dom.DeferredNode` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.DeferredNotationImpl; org.apache.xerces.dom.DeferredElementImpl; org.apache.xerces.dom.DeferredEntityImpl
Stage 3B neighbours: org.apache.xerces.dom.DeferredNotationImpl [w=0.710597321095, G_raw=true]; org.apache.xerces.dom.DeferredElementImpl [w=0.69906642722, G_raw=true]; org.apache.xerces.dom.DeferredEntityImpl [w=0.675668279422, G_raw=true]

### `org.apache.xerces.dom3.as.ASAttributeDeclaration` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=0.6666666666666666; degree=6
Stage 3A neighbours: org.apache.xerces.dom3.as.ASElementDeclaration; org.apache.xerces.xs.XSAttributeDeclaration; org.apache.xerces.impl.xs.XSAttributeDecl
Stage 3B neighbours: org.apache.xerces.dom3.as.ASElementDeclaration [w=0.837097448691, G_raw=true]; org.apache.xerces.xs.XSAttributeDeclaration [w=0.760430580371, G_raw=false]; org.apache.xerces.dom3.as.ASEntityDeclaration [w=0.744859995593, G_raw=false]

### `org.apache.xerces.dom3.as.ASContentModel` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom3.as.ASModel; org.apache.xerces.dom.ASModelImpl; org.apache.xerces.dom3.as.DocumentAS
Stage 3B neighbours: org.apache.xerces.dom3.as.ASModel [w=0.814371148758, G_raw=true]; org.apache.xerces.dom.ASModelImpl [w=0.693173274073, G_raw=true]; org.apache.xerces.dom3.as.DocumentAS [w=0.680462088133, G_raw=false]

### `org.apache.xerces.dom3.as.ASDataType` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=0.6666666666666666; degree=3
Stage 3A neighbours: org.apache.xerces.dom3.as.ASAttributeDeclaration; org.apache.xerces.dom3.as.ASObject; org.apache.xerces.dom3.as.ASModel
Stage 3B neighbours: org.apache.xerces.dom3.as.ASAttributeDeclaration [w=0.699327839713, G_raw=true]; org.apache.xerces.dom3.as.ASObject [w=0.637516311871, G_raw=false]; org.apache.xerces.dom3.as.ASEntityDeclaration [w=0.625673671048, G_raw=false]

### `org.apache.xerces.dom3.as.ASElementDeclaration` — empty_body_fixed_sample
body_empty=true; body_tokens_truncated=0; retention=0.6666666666666666; degree=6
Stage 3A neighbours: org.apache.xerces.dom3.as.ASAttributeDeclaration; org.apache.xerces.dom3.as.ASEntityDeclaration; org.apache.xerces.xs.XSElementDeclaration
Stage 3B neighbours: org.apache.xerces.dom3.as.ASAttributeDeclaration [w=0.837097448691, G_raw=true]; org.apache.xerces.dom3.as.ASEntityDeclaration [w=0.796437335347, G_raw=false]; org.apache.xerces.dom3.as.ASModel [w=0.754333519812, G_raw=true]

### `org.apache.xerces.dom.ObjectFactory` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.ObjectFactory; org.apache.xerces.parsers.ObjectFactory; org.apache.xerces.xinclude.ObjectFactory
Stage 3B neighbours: org.apache.xerces.impl.dv.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.xinclude.ObjectFactory [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.ObjectFactory` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory; org.apache.xerces.parsers.ObjectFactory; org.apache.xerces.xinclude.ObjectFactory
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.xinclude.ObjectFactory [w=1, G_raw=false]

### `org.apache.xerces.parsers.ObjectFactory` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory; org.apache.xerces.impl.dv.ObjectFactory; org.apache.xerces.xinclude.ObjectFactory
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.impl.dv.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.xinclude.ObjectFactory [w=1, G_raw=false]

### `org.apache.xerces.xinclude.ObjectFactory` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory; org.apache.xerces.impl.dv.ObjectFactory; org.apache.xerces.parsers.ObjectFactory
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.impl.dv.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory [w=1, G_raw=false]

### `org.apache.xml.serialize.ObjectFactory` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory; org.apache.xerces.impl.dv.ObjectFactory; org.apache.xerces.parsers.ObjectFactory
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.impl.dv.ObjectFactory [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory [w=1, G_raw=false]

### `org.apache.xerces.dom.ObjectFactory$ConfigurationError` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError; org.apache.xerces.parsers.ObjectFactory$ConfigurationError; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError
Stage 3B neighbours: org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError; org.apache.xerces.parsers.ObjectFactory$ConfigurationError; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError [w=1, G_raw=false]

### `org.apache.xerces.parsers.ObjectFactory$ConfigurationError` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.xinclude.ObjectFactory$ConfigurationError [w=1, G_raw=false]

### `org.apache.xerces.xinclude.ObjectFactory$ConfigurationError` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError; org.apache.xerces.parsers.ObjectFactory$ConfigurationError
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory$ConfigurationError [w=1, G_raw=false]

### `org.apache.xml.serialize.ObjectFactory$ConfigurationError` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError; org.apache.xerces.parsers.ObjectFactory$ConfigurationError
Stage 3B neighbours: org.apache.xerces.dom.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError [w=1, G_raw=false]; org.apache.xerces.parsers.ObjectFactory$ConfigurationError [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport; org.apache.xerces.parsers.SecuritySupport; org.apache.xerces.xinclude.SecuritySupport
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport; org.apache.xerces.parsers.SecuritySupport; org.apache.xerces.xinclude.SecuritySupport
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport; org.apache.xerces.impl.dv.SecuritySupport; org.apache.xerces.xinclude.SecuritySupport
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport; org.apache.xerces.impl.dv.SecuritySupport; org.apache.xerces.parsers.SecuritySupport
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport; org.apache.xerces.impl.dv.SecuritySupport; org.apache.xerces.parsers.SecuritySupport
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$1` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1; org.apache.xerces.xinclude.SecuritySupport$1
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$1 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$1` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1; org.apache.xerces.xinclude.SecuritySupport$1
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$1 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$1` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.xinclude.SecuritySupport$1
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$1 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$1` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$1 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$1` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$1; org.apache.xerces.impl.dv.SecuritySupport$1; org.apache.xerces.parsers.SecuritySupport$1
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$1 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$1 [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$2` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$2; org.apache.xerces.parsers.SecuritySupport$2; org.apache.xerces.xinclude.SecuritySupport$2
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$2 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$2` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$2; org.apache.xerces.parsers.SecuritySupport$2; org.apache.xerces.xinclude.SecuritySupport$2
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$2 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$2` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$2; org.apache.xerces.impl.dv.SecuritySupport$2; org.apache.xerces.xinclude.SecuritySupport$2
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$2 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$2` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$2; org.apache.xerces.impl.dv.SecuritySupport$2; org.apache.xerces.parsers.SecuritySupport$2
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$2 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$2` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$2; org.apache.xerces.impl.dv.SecuritySupport$2; org.apache.xerces.parsers.SecuritySupport$2
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$2 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$2 [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$3` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$3; org.apache.xerces.parsers.SecuritySupport$3; org.apache.xerces.xinclude.SecuritySupport$3
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$3 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$3` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$3; org.apache.xerces.parsers.SecuritySupport$3; org.apache.xerces.xinclude.SecuritySupport$3
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$3 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$3` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$3; org.apache.xerces.impl.dv.SecuritySupport$3; org.apache.xerces.xinclude.SecuritySupport$3
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$3 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$3` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$3; org.apache.xerces.impl.dv.SecuritySupport$3; org.apache.xerces.parsers.SecuritySupport$3
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$3 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$3` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$3; org.apache.xerces.impl.dv.SecuritySupport$3; org.apache.xerces.parsers.SecuritySupport$3
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$3 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$3 [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$4` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=5
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$4; org.apache.xerces.parsers.SecuritySupport$4; org.apache.xerces.xinclude.SecuritySupport$4
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$4 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$4` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=5
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$4; org.apache.xerces.parsers.SecuritySupport$4; org.apache.xerces.xinclude.SecuritySupport$4
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$4 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$4` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=5
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$4; org.apache.xerces.impl.dv.SecuritySupport$4; org.apache.xerces.xinclude.SecuritySupport$4
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$4 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$4` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$4; org.apache.xerces.impl.dv.SecuritySupport$4; org.apache.xerces.parsers.SecuritySupport$4
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$4 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$4` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$4; org.apache.xerces.impl.dv.SecuritySupport$4; org.apache.xerces.parsers.SecuritySupport$4
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$4 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$4 [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$5` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$5; org.apache.xerces.parsers.SecuritySupport$5; org.apache.xerces.xinclude.SecuritySupport$5
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$5 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$5` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$5; org.apache.xerces.parsers.SecuritySupport$5; org.apache.xerces.xinclude.SecuritySupport$5
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$5 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$5` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$5; org.apache.xerces.impl.dv.SecuritySupport$5; org.apache.xerces.xinclude.SecuritySupport$5
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$5 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$5` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$5; org.apache.xerces.impl.dv.SecuritySupport$5; org.apache.xerces.parsers.SecuritySupport$5
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$5 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$5` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$5; org.apache.xerces.impl.dv.SecuritySupport$5; org.apache.xerces.parsers.SecuritySupport$5
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$5 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$5 [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$6` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$6; org.apache.xerces.parsers.SecuritySupport$6; org.apache.xerces.xinclude.SecuritySupport$6
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$6 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$6` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$6; org.apache.xerces.parsers.SecuritySupport$6; org.apache.xerces.xinclude.SecuritySupport$6
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$6 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$6` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$6; org.apache.xerces.impl.dv.SecuritySupport$6; org.apache.xerces.xinclude.SecuritySupport$6
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$6 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$6` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$6; org.apache.xerces.impl.dv.SecuritySupport$6; org.apache.xerces.parsers.SecuritySupport$6
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$6 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$6` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$6; org.apache.xerces.impl.dv.SecuritySupport$6; org.apache.xerces.parsers.SecuritySupport$6
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$6 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$6 [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$7` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=5
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$7; org.apache.xerces.parsers.SecuritySupport$7; org.apache.xerces.xinclude.SecuritySupport$7
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$7 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$7` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$7; org.apache.xerces.parsers.SecuritySupport$7; org.apache.xerces.xinclude.SecuritySupport$7
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$7 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$7` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$7; org.apache.xerces.impl.dv.SecuritySupport$7; org.apache.xerces.xinclude.SecuritySupport$7
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$7 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$7` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$7; org.apache.xerces.impl.dv.SecuritySupport$7; org.apache.xerces.parsers.SecuritySupport$7
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$7 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$7` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$7; org.apache.xerces.impl.dv.SecuritySupport$7; org.apache.xerces.parsers.SecuritySupport$7
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$7 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$7 [w=1, G_raw=false]

### `org.apache.xerces.dom.SecuritySupport$8` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.impl.dv.SecuritySupport$8; org.apache.xerces.parsers.SecuritySupport$8; org.apache.xerces.xinclude.SecuritySupport$8
Stage 3B neighbours: org.apache.xerces.impl.dv.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$8 [w=1, G_raw=false]

### `org.apache.xerces.impl.dv.SecuritySupport$8` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$8; org.apache.xerces.parsers.SecuritySupport$8; org.apache.xerces.xinclude.SecuritySupport$8
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$8 [w=1, G_raw=false]

### `org.apache.xerces.parsers.SecuritySupport$8` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=4
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$8; org.apache.xerces.impl.dv.SecuritySupport$8; org.apache.xerces.xinclude.SecuritySupport$8
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.xinclude.SecuritySupport$8 [w=1, G_raw=false]

### `org.apache.xerces.xinclude.SecuritySupport$8` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$8; org.apache.xerces.impl.dv.SecuritySupport$8; org.apache.xerces.parsers.SecuritySupport$8
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$8 [w=1, G_raw=false]

### `org.apache.xml.serialize.SecuritySupport$8` — xerces_collision_group
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=3
Stage 3A neighbours: org.apache.xerces.dom.SecuritySupport$8; org.apache.xerces.impl.dv.SecuritySupport$8; org.apache.xerces.parsers.SecuritySupport$8
Stage 3B neighbours: org.apache.xerces.dom.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.impl.dv.SecuritySupport$8 [w=1, G_raw=false]; org.apache.xerces.parsers.SecuritySupport$8 [w=1, G_raw=false]

### `org.apache.xerces.util.XMLGrammarPoolImpl` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=14
Stage 3A neighbours: org.apache.xerces.xni.grammars.XMLGrammarPool; org.apache.xerces.jaxp.validation.XMLSchemaFactory$XMLGrammarPoolWrapper; org.apache.xerces.jaxp.validation.SoftReferenceGrammarPool
Stage 3B neighbours: org.apache.xerces.xni.grammars.XMLGrammarPool [w=0.846888091745, G_raw=true]; org.apache.xerces.jaxp.validation.SoftReferenceGrammarPool [w=0.845723319725, G_raw=false]; org.apache.xerces.jaxp.validation.XMLSchemaFactory$XMLGrammarPoolWrapper [w=0.838176147739, G_raw=false]

### `org.apache.xerces.dom.DeferredElementImpl` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=1.0; degree=11
Stage 3A neighbours: org.apache.xerces.dom.DeferredElementDefinitionImpl; org.apache.xerces.dom.DeferredElementNSImpl; org.apache.xerces.dom.DeferredEntityImpl
Stage 3B neighbours: org.apache.xerces.dom.DeferredElementDefinitionImpl [w=0.932201200318, G_raw=false]; org.apache.xerces.dom.DeferredElementNSImpl [w=0.906073880425, G_raw=false]; org.apache.xerces.dom.DeferredEntityImpl [w=0.842116508198, G_raw=false]

### `org.apache.xerces.util.NamespaceSupport` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=11
Stage 3A neighbours: org.apache.xerces.xni.NamespaceContext; org.apache.xerces.xinclude.MultipleScopeNamespaceSupport; org.apache.xerces.jaxp.validation.DOMValidatorHelper$DOMNamespaceContext
Stage 3B neighbours: org.apache.xerces.jaxp.validation.DOMValidatorHelper$DOMNamespaceContext [w=0.833617920716, G_raw=true]; org.apache.xerces.xinclude.MultipleScopeNamespaceSupport [w=0.815132324939, G_raw=true]; org.apache.xerces.util.JAXPNamespaceContextWrapper [w=0.80543683281, G_raw=false]

### `org.apache.xerces.dom.NodeImpl` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=10
Stage 3A neighbours: org.apache.xerces.dom.CoreDocumentImpl; org.apache.xerces.dom.DocumentImpl; org.apache.xerces.impl.xs.opti.NodeImpl
Stage 3B neighbours: org.apache.xerces.dom.DocumentImpl [w=0.727822660801, G_raw=true]; org.apache.xerces.dom.ElementImpl [w=0.71753864648, G_raw=true]; org.apache.xerces.dom.CoreDocumentImpl [w=0.706390337398, G_raw=true]

### `org.apache.xerces.util.ErrorHandlerWrapper` — highest_stage3b_degree
body_empty=false; body_tokens_truncated=0; retention=0.6666666666666666; degree=10
Stage 3A neighbours: org.apache.xerces.util.DOMErrorHandlerWrapper; org.apache.xerces.util.ErrorHandlerProxy; org.apache.xerces.impl.xs.traversers.XSDHandler$SAX2XNIUtil
Stage 3B neighbours: org.apache.xerces.util.DOMErrorHandlerWrapper [w=0.852719388569, G_raw=false]; org.apache.xerces.util.ErrorHandlerProxy [w=0.807026717839, G_raw=true]; org.apache.xerces.jaxp.validation.DraconianErrorHandler [w=0.773130939203, G_raw=false]
