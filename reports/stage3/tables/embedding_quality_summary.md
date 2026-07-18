# Stage 3B embedding quality summary

This report validates isolated declaration-plus-method-body embeddings only. No semantic graph, nearest-neighbour graph, optimization, seed, or decomposition analysis was performed.

Frozen runtime: SentenceTransformer `nomic-ai/nomic-embed-code` revision `9a0457648f060c4279d4a3982d2d27a4df6fac59`, dimension 3584, MPS float16, batch 8, stored float32.

## Numerical and tokenizer summary

| Subject | Classes | Dim | Norm min/mean/median/std/max | NaN | Inf | Zero | Max model tokens | Contract body truncations | Unexpected tokenizer truncations | Duplicate text groups | Duplicate embedding groups |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| jpetstore | 24 | 3584 | 0.999774450/1.000030176/1.000056953/0.000143095/1.000248572 | 0 | 0 | 0 | 466 | 0 | 0 | 0 | 0 |
| daytrader | 53 | 3584 | 0.999720028/1.000020184/1.000025978/0.000160052/1.000278438 | 0 | 0 | 0 | 975 | 1 | 0 | 0 | 0 |
| xerces | 814 | 3584 | 0.999556654/0.999994727/0.999989768/0.000156991/1.000417329 | 0 | 0 | 0 | 1833 | 7 | 0 | 11 | 11 |

## Stage 3A versus Stage 3B shift

Effectively unchanged means cosine distance <= 1e-06. Materially shifted is a diagnostic flag for cosine distance >= 0.05; neither threshold is a quality judgment.

* **jpetstore**: cosine min/mean/median/std/max = 0.693240821/0.794925651/0.801656939/0.048129038/0.866353332; unchanged=0; materially_shifted=24; empty-body distance mean=0.207882298; non-empty-body distance mean=0.203918135; body-token correlation=-0.4139905810132448
  Largest shifts: org.mybatis.jpetstore.service.OrderService, org.mybatis.jpetstore.domain.Product, org.mybatis.jpetstore.domain.Category, org.mybatis.jpetstore.service.CatalogService, org.mybatis.jpetstore.mapper.CategoryMapper
  Smallest non-empty shifts: org.mybatis.jpetstore.domain.Order, org.mybatis.jpetstore.web.actions.AccountActionBean, org.mybatis.jpetstore.web.actions.CatalogActionBean, org.mybatis.jpetstore.web.actions.CartActionBean, org.mybatis.jpetstore.web.actions.OrderActionBean
* **daytrader**: cosine min/mean/median/std/max = 0.518285732/0.816189346/0.834528426/0.074751163/0.925194833; unchanged=0; materially_shifted=53; empty-body distance mean=0.124061720; non-empty-body distance mean=0.188688118; body-token correlation=-0.2754616001346665
  Largest shifts: com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage$1, com.ibm.websphere.samples.daytrader.util.CompleteOrderThread, com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage, com.ibm.websphere.samples.daytrader.web.jsf.LoginValidator, com.ibm.websphere.samples.daytrader.web.websocket.JsonMessage
  Smallest non-empty shifts: com.ibm.websphere.samples.daytrader.web.jsf.AccountDataJSF, com.ibm.websphere.samples.daytrader.web.jsf.TradeConfigJSF, com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean, com.ibm.websphere.samples.daytrader.entities.QuoteDataBean, com.ibm.websphere.samples.daytrader.entities.HoldingDataBean
* **xerces**: cosine min/mean/median/std/max = 0.536404763/0.821678785/0.830948259/0.066432307/0.944000960; unchanged=0; materially_shifted=814; empty-body distance mean=0.110105018; non-empty-body distance mean=0.190116523; body-token correlation=-0.18966214081440685
  Largest shifts: org.apache.xerces.impl.xs.traversers.OneAttr, org.apache.xerces.parsers.SAXParser, org.apache.xerces.impl.xs.traversers.XSAnnotationInfo, org.apache.xml.serialize.ElementState, org.apache.xerces.parsers.XMLGrammarParser
  Smallest non-empty shifts: org.apache.xerces.parsers.AbstractXMLDocumentParser, org.apache.xerces.parsers.SecureProcessingConfiguration$InternalEntityMonitor, org.apache.xerces.parsers.DOMParserImpl$AbortHandler, org.apache.xerces.impl.xs.SchemaGrammar$Schema4Annotations, org.apache.xerces.impl.xs.opti.DefaultXMLDocumentHandler

## Duplicate diagnostics

* jpetstore: Stage 3B duplicate semantic-text groups=0; duplicate embedding groups=0; non-identical-text embedding collisions=0.
* daytrader: Stage 3B duplicate semantic-text groups=0; duplicate embedding groups=0; non-identical-text embedding collisions=0.
* xerces: Stage 3B duplicate semantic-text groups=11; duplicate embedding groups=11; non-identical-text embedding collisions=0.

Xerces has 11 expected duplicate-text groups under the frozen simple-name input contract. The classes were not deduplicated.

## Acceptance checks

* All rows have the expected class mapping and dimension.
* NaN, Inf, zero-vector, norm, and save/load checks passed.
* Actual tokenizer counts used truncation=false; declaration truncation is zero and unexpected tokenizer truncation is zero.
* Stage 3A embeddings were read diagnostically only; they were not used as a Stage 3B cache.
