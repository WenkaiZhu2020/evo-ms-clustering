# Stage 3B embedding manual audit

Fixed selection: first five sorted classes; five largest Stage 3A-to-Stage 3B shifts; five smallest non-empty-body shifts; all Xerces duplicate-text collision members; all body-truncated classes; and the first five empty-body classes. Duplicate classes are listed once. No neighbours or graph edges are included.

## jpetstore

### `org.mybatis.jpetstore.domain.Account` — first_sorted
declaration_tokens=207; body_tokens=45; body_evidence_summary=`invoke address1 address2 banner name city country email favourite category id first name language preference last password phone state status username zip banner option list option address1 address2 city country email favourite category id `
stage3a_stage3b_cosine=0.804159757197; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.domain.Cart` — first_sorted
declaration_tokens=75; body_tokens=37; body_evidence_summary=`invoke create item map list add item increment quantity invoke branch jump create map list contains id key all cart items iterator cart items iterator number size sub total reduce zero increment quantity id remove branch jump`
stage3a_stage3b_cosine=0.775016936335; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.domain.CartItem` — first_sorted
declaration_tokens=55; body_tokens=13; body_evidence_summary=`invoke calculate total invoke item item quantity total increment quantity calculate stock stock`
stage3a_stage3b_cosine=0.820891433566; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.domain.Category` — first_sorted
declaration_tokens=40; body_tokens=12; body_evidence_summary=`invoke category id description name category id trim invoke description name string`
stage3a_stage3b_cosine=0.736627561047; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.domain.Item` — first_sorted
declaration_tokens=155; body_tokens=37; body_evidence_summary=`invoke attribute1 attribute2 attribute3 attribute4 attribute5 item id list price product quantity status supplier id unit cost attribute1 attribute2 attribute3 attribute4 attribute5 item trim invoke list price product quantity status suppli`
stage3a_stage3b_cosine=0.763576969836; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.service.OrderService` — largest_shift
declaration_tokens=32; body_tokens=28; body_evidence_summary=`invoke item mapper order sequence line next id create invoke branch jump sequence mapper runtime exception make concat constants order each line item orders username insert each ordernum`
stage3a_stage3b_cosine=0.693240820669; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.domain.Product` — largest_shift
declaration_tokens=51; body_tokens=14; body_evidence_summary=`invoke category id description name product id category description name product trim invoke string`
stage3a_stage3b_cosine=0.706054533551; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.service.CatalogService` — largest_shift
declaration_tokens=59; body_tokens=23; body_evidence_summary=`invoke category mapper item product category invoke mapper list item list product stock branch jump search create measure branch jump make concat constants`
stage3a_stage3b_cosine=0.748691153051; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.mapper.CategoryMapper` — largest_shift
declaration_tokens=16; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.752864160004; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.mybatis.jpetstore.domain.Order` — smallest_nonempty_shift
declaration_tokens=386; body_tokens=67; body_evidence_summary=`invoke create line items add line item create invoke items add item bill address1 bill address2 city country state first name last name zip card type courier credit card expiry date locale order date order id ship address1 ship address2 cit`
stage3a_stage3b_cosine=0.866353331929; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.web.actions.AccountActionBean` — smallest_nonempty_shift
declaration_tokens=107; body_tokens=51; body_evidence_summary=`unmodifiable list create invoke language category english japanese fish dogs reptiles cats birds invoke create account clear account my list authenticated edit service catalog my edit form categories category languages language password use`
stage3a_stage3b_cosine=0.861789726076; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.web.actions.CatalogActionBean` — smallest_nonempty_shift
declaration_tokens=158; body_tokens=34; body_evidence_summary=`invoke clear keyword category id list product item category id list item keyword product search products branch jump invoke create catalog service please enter press button view branch jump create catalog service view main`
stage3a_stage3b_cosine=0.861646664364; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.web.actions.CartActionBean` — smallest_nonempty_shift
declaration_tokens=70; body_tokens=32; body_evidence_summary=`invoke create cart add item cart branch jump invoke create working id catalog service invalid cannot check out clear working item id remove branch jump invalid cannot attempted update quantities context view`
stage3a_stage3b_cosine=0.856341793238; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.web.actions.OrderActionBean` — smallest_nonempty_shift
declaration_tokens=99; body_tokens=64; body_evidence_summary=`unmodifiable list create invoke card type visa master american express invoke create order clear order shipping address required confirmed list credit card types type id confirmed shipping address required orders context service branch jump`
stage3a_stage3b_cosine=0.855631336994; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.mybatis.jpetstore.mapper.AccountMapper` — empty_body_fixed_sample
declaration_tokens=61; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.808350466789; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.mybatis.jpetstore.mapper.ItemMapper` — empty_body_fixed_sample
declaration_tokens=33; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.822809404443; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.mybatis.jpetstore.mapper.LineItemMapper` — empty_body_fixed_sample
declaration_tokens=24; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.822455690586; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.mybatis.jpetstore.mapper.OrderMapper` — empty_body_fixed_sample
declaration_tokens=31; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.75818968127; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.mybatis.jpetstore.mapper.ProductMapper` — empty_body_fixed_sample
declaration_tokens=26; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.781000388045; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

## daytrader

### `com.ibm.websphere.samples.daytrader.TradeAction` — first_sorted
declaration_tokens=264; body_tokens=102; body_evidence_summary=`print trace create invoke branch jump market summary lock next cached msdb trade remote shared cache mode jpa enabled none disabled unable determine create trade invoke branch jump trace buy update quote price volume cancel order unsupporte`
stage3a_stage3b_cosine=0.824168416375; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.TradeServices` — first_sorted
declaration_tokens=216; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.86936304712; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `com.ibm.websphere.samples.daytrader.beans.MarketSummaryDataBean` — first_sorted
declaration_tokens=122; body_tokens=46; body_evidence_summary=`invoke gain percent compute gain percent invoke create compute branch jump open tsia random instance create branch jump summary date tsia top gainers top losers volume print log open summary date gainers losers volume html current json buil`
stage3a_stage3b_cosine=0.866445759987; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.beans.RunStatsDataBean` — first_sorted
declaration_tokens=190; body_tokens=32; body_evidence_summary=`invoke buy order count cancelled order count deleted holding user open sell sum login sum logout trade stock trade user buy cancelled deleted holding open sell login logout stock string create invoke`
stage3a_stage3b_cosine=0.86368475982; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.direct.KeySequenceDirect` — first_sorted
declaration_tokens=32; body_tokens=33; body_evidence_summary=`create invoke key map invoke alloc block branch jump create keyblocksize key map exception select keygenejb kg where keyname update insert into keyval values set next id trace branch jump sequence pk entity`
stage3a_stage3b_cosine=0.852358185606; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage$1` — largest_shift
declaration_tokens=7; body_tokens=15; body_evidence_summary=`ordinal invoke measure create jump map javax json stream parser event key name value string`
stage3a_stage3b_cosine=0.518285732371; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.util.CompleteOrderThread` — largest_shift
declaration_tokens=13; body_tokens=15; body_evidence_summary=`invoke order id two phase invoke create branch jump order id two phase ejb exception`
stage3a_stage3b_cosine=0.620564029559; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage` — largest_shift
declaration_tokens=20; body_tokens=18; body_evidence_summary=`invoke decoded action decoding trace create invoke branch jump map javax json stream parser event decoded action failed`
stage3a_stage3b_cosine=0.651546696653; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.web.jsf.LoginValidator` — largest_shift
declaration_tokens=24; body_tokens=25; body_evidence_summary=`compile invoke login regex pattern invoke validate branch jump create pattern matcher severity error validator exception validating submitted login name username validation failed please provide`
stage3a_stage3b_cosine=0.693649656977; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.web.websocket.JsonMessage` — largest_shift
declaration_tokens=25; body_tokens=5; body_evidence_summary=`invoke key value key value`
stage3a_stage3b_cosine=0.702191818558; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.web.jsf.AccountDataJSF` — smallest_nonempty_shift
declaration_tokens=307; body_tokens=76; body_evidence_summary=`value invoke number orders order rows account data gain percent invoke balance holdings total sum cash open account id all orders balance closed creation date current time gain html print percent html print holdings total last login login c`
stage3a_stage3b_cosine=0.925194832543; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.web.jsf.TradeConfigJSF` — smallest_nonempty_shift
declaration_tokens=295; body_tokens=134; body_evidence_summary=`trace invoke runtime mode order processing names max users quotes market summary interval web prim iterations percent sent websocket publish quote price change run display alerts use remote ejb action list result build database tables creat`
stage3a_stage3b_cosine=0.905446117839; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean` — smallest_nonempty_shift
declaration_tokens=323; body_tokens=164; body_evidence_summary=`trace invoke branch jump trade slsb create jndi lookups ejb jms resources buy invoke branch jump create entity manager ejb exception trade slsb failed cancel order entity manager two complete order completed exception two attempt already be`
stage3a_stage3b_cosine=0.887016105183; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.entities.QuoteDataBean` — smallest_nonempty_shift
declaration_tokens=137; body_tokens=43; body_evidence_summary=`invoke symbol invoke change branch jump symbol change change1 company name high low open open1 price random instance create incorporated volume hash code branch jump print log change1 company name high low open open1 price volume html strin`
stage3a_stage3b_cosine=0.885197259249; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.entities.HoldingDataBean` — smallest_nonempty_shift
declaration_tokens=138; body_tokens=36; body_evidence_summary=`invoke quote invoke quote id branch jump holding id account holding purchase date purchase price quantity symbol branch jump random instance create hash code print log account date price quantity html string create data string data`
stage3a_stage3b_cosine=0.880575420177; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `com.ibm.websphere.samples.daytrader.direct.TradeDirect` — body_truncated
declaration_tokens=678; body_tokens=256; body_evidence_summary=`create invoke datasource ds name zero conn count lock initialized invoke branch jump global txn session initialized branch jump global txn session buy create context trade failed queue order committing transaction error rolling back cancel `
stage3a_stage3b_cosine=0.854781793554; collision_stage3a=none; collision_stage3b=none; body_truncated=31; body_empty=false

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal` — empty_body_fixed_sample
declaration_tokens=49; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.881459020687; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote` — empty_body_fixed_sample
declaration_tokens=49; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.883855095779; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage` — empty_body_fixed_sample
declaration_tokens=19; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.869075958091; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

## xerces

### `org.apache.xerces.dom.ASDOMImplementationImpl` — first_sorted
declaration_tokens=48; body_tokens=17; body_evidence_summary=`create invoke singleton invoke create domas builder domas writer dom exception not supported err dom implementation singleton`
stage3a_stage3b_cosine=0.836032110283; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.ASModelImpl` — first_sorted
declaration_tokens=319; body_tokens=66; body_evidence_summary=`invoke create namespace aware grammar models invoke create namespace aware grammar models add model element clone object dom exception not supported err attribute declaration dom exception not supported err content model s2 element declarat`
stage3a_stage3b_cosine=0.895817441274; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.AttrImpl` — first_sorted
declaration_tokens=288; body_tokens=118; body_evidence_summary=`invoke value has string value invoke name check normalization after insert normalized branch jump next sibling s0 s2 s1 check normalization after remove normalized branch jump next sibling s0 s1 clone node specified child nodes synchronize `
stage3a_stage3b_cosine=0.845131838744; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.AttrNSImpl` — first_sorted
declaration_tokens=68; body_tokens=42; body_evidence_summary=`invoke invoke name name namespace uri synchronize data branch jump namespace uri synchronize data branch jump prefix type type derived dom rename check domns err create error checking xmlns dom exception prefix string create error checking `
stage3a_stage3b_cosine=0.811296433791; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.AttributeMap` — first_sorted
declaration_tokens=148; body_tokens=77; body_evidence_summary=`has defaults invoke branch jump nodes add item attr node invoke branch jump create owner nodes clone content create owner node clone map content internal remove named item dom exception not found err internal remove named ns removed attr er`
stage3a_stage3b_cosine=0.831314945548; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.xs.traversers.OneAttr` — largest_shift
declaration_tokens=5; body_tokens=6; body_evidence_summary=`invoke name dv index value dflt`
stage3a_stage3b_cosine=0.536404763387; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SAXParser` — largest_shift
declaration_tokens=11; body_tokens=23; body_evidence_summary=`newarray create recognized features properties invoke invoke property branch jump configuration recognized features properties org apache xerces xni parser xml parsers include aware`
stage3a_stage3b_cosine=0.566495472171; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.xs.traversers.XSAnnotationInfo` — largest_shift
declaration_tokens=6; body_tokens=13; body_evidence_summary=`invoke annotation line column offset character offset invoke branch jump annotation line column`
stage3a_stage3b_cosine=0.571352679656; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.ElementState` — largest_shift
declaration_tokens=6; body_tokens=1; body_evidence_summary=`invoke`
stage3a_stage3b_cosine=0.598663651499; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.XMLGrammarParser` — largest_shift
declaration_tokens=11; body_tokens=12; body_evidence_summary=`property invoke configuration org apache xerces xni parser xml parsers include aware`
stage3a_stage3b_cosine=0.606565288821; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.AbstractXMLDocumentParser` — smallest_nonempty_shift
declaration_tokens=598; body_tokens=61; body_evidence_summary=`dtd content model handler invoke any attribute decl characters comment doctype decl element element empty empty end invoke end attlist cdata conditional content model dtd document external subset general entity group entity external source `
stage3a_stage3b_cosine=0.944000959687; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecureProcessingConfiguration$InternalEntityMonitor` — smallest_nonempty_shift
declaration_tokens=306; body_tokens=41; body_evidence_summary=`invoke attribute decl branch jump invoke dtd handler comment branch jump dtd handler element decl end attlist end conditional external subset entity external entity source ignored characters internal length notation processing instruction s`
stage3a_stage3b_cosine=0.94001860216; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.DOMParserImpl$AbortHandler` — smallest_nonempty_shift
declaration_tokens=591; body_tokens=60; body_evidence_summary=`invoke any instance attribute decl instance characters comment doctype decl element element empty empty end attlist end cdata conditional content model dtd document external subset general entity group entity external dtd content model sour`
stage3a_stage3b_cosine=0.93913166846; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.xs.SchemaGrammar$Schema4Annotations` — smallest_nonempty_shift
declaration_tokens=367; body_tokens=109; body_evidence_summary=`create invoke instance anonymous invoke create uri schemaforschema target namespace grammar description context type global attr decls grp elem group notation id constraint ext all sg schema ns elt annotation documentation appinfo name decl`
stage3a_stage3b_cosine=0.937700637553; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.xs.opti.DefaultXMLDocumentHandler` — smallest_nonempty_shift
declaration_tokens=614; body_tokens=64; body_evidence_summary=`invoke any attribute decl characters comment doctype decl element element empty empty end attlist end cdata conditional content model dtd document external subset general entity group entity prefix mapping external dtd content model source `
stage3a_stage3b_cosine=0.937090106362; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.ObjectFactory` — xerces_duplicate_text_group
declaration_tokens=70; body_tokens=54; body_evidence_summary=`debug enabled invoke xerces properties last modified invoke create object create object instance branch jump debug separator last modified xerces properties configuration error found system java home lib provider cannot using entermonitor c`
stage3a_stage3b_cosine=0.717626614384; collision_stage3a=stage3a_001; collision_stage3b=stage3b_001; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.ObjectFactory` — xerces_duplicate_text_group
declaration_tokens=70; body_tokens=54; body_evidence_summary=`debug enabled invoke xerces properties last modified invoke create object create object instance branch jump debug separator last modified xerces properties configuration error found system java home lib provider cannot using entermonitor c`
stage3a_stage3b_cosine=0.717626614384; collision_stage3a=stage3a_001; collision_stage3b=stage3b_001; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.ObjectFactory` — xerces_duplicate_text_group
declaration_tokens=70; body_tokens=54; body_evidence_summary=`debug enabled invoke xerces properties last modified invoke create object create object instance branch jump debug separator last modified xerces properties configuration error found system java home lib provider cannot using entermonitor c`
stage3a_stage3b_cosine=0.717626614384; collision_stage3a=stage3a_001; collision_stage3b=stage3b_001; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.ObjectFactory` — xerces_duplicate_text_group
declaration_tokens=70; body_tokens=54; body_evidence_summary=`debug enabled invoke xerces properties last modified invoke create object create object instance branch jump debug separator last modified xerces properties configuration error found system java home lib provider cannot using entermonitor c`
stage3a_stage3b_cosine=0.717626614384; collision_stage3a=stage3a_001; collision_stage3b=stage3b_001; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.ObjectFactory` — xerces_duplicate_text_group
declaration_tokens=70; body_tokens=54; body_evidence_summary=`debug enabled invoke xerces properties last modified invoke create object create object instance branch jump debug separator last modified xerces properties configuration error found system java home lib provider cannot using entermonitor c`
stage3a_stage3b_cosine=0.717626614384; collision_stage3a=stage3a_001; collision_stage3b=stage3b_001; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.ObjectFactory$ConfigurationError` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke exception exception`
stage3a_stage3b_cosine=0.797944651881; collision_stage3a=stage3a_002; collision_stage3b=stage3b_002; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke exception exception`
stage3a_stage3b_cosine=0.797944651881; collision_stage3a=stage3a_002; collision_stage3b=stage3b_002; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.ObjectFactory$ConfigurationError` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke exception exception`
stage3a_stage3b_cosine=0.797944651881; collision_stage3a=stage3a_002; collision_stage3b=stage3b_002; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.ObjectFactory$ConfigurationError` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke exception exception`
stage3a_stage3b_cosine=0.797944651881; collision_stage3a=stage3a_002; collision_stage3b=stage3b_002; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.ObjectFactory$ConfigurationError` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke exception exception`
stage3a_stage3b_cosine=0.797944651881; collision_stage3a=stage3a_002; collision_stage3b=stage3b_002; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport` — xerces_duplicate_text_group
declaration_tokens=60; body_tokens=25; body_evidence_summary=`invoke context loader privileged create invoke file exists value create file input stream exception last modified value parent loader privileged resource stream system system property`
stage3a_stage3b_cosine=0.81686155545; collision_stage3a=stage3a_003; collision_stage3b=stage3b_003; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport` — xerces_duplicate_text_group
declaration_tokens=60; body_tokens=25; body_evidence_summary=`invoke context loader privileged create invoke file exists value create file input stream exception last modified value parent loader privileged resource stream system system property`
stage3a_stage3b_cosine=0.81686155545; collision_stage3a=stage3a_003; collision_stage3b=stage3b_003; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport` — xerces_duplicate_text_group
declaration_tokens=60; body_tokens=25; body_evidence_summary=`invoke context loader privileged create invoke file exists value create file input stream exception last modified value parent loader privileged resource stream system system property`
stage3a_stage3b_cosine=0.81686155545; collision_stage3a=stage3a_003; collision_stage3b=stage3b_003; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport` — xerces_duplicate_text_group
declaration_tokens=60; body_tokens=25; body_evidence_summary=`invoke context loader privileged create invoke file exists value create file input stream exception last modified value parent loader privileged resource stream system system property`
stage3a_stage3b_cosine=0.81686155545; collision_stage3a=stage3a_003; collision_stage3b=stage3b_003; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport` — xerces_duplicate_text_group
declaration_tokens=60; body_tokens=25; body_evidence_summary=`invoke context loader privileged create invoke file exists value create file input stream exception last modified value parent loader privileged resource stream system system property`
stage3a_stage3b_cosine=0.81686155545; collision_stage3a=stage3a_003; collision_stage3b=stage3b_003; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$1` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.740808968994; collision_stage3a=stage3a_004; collision_stage3b=stage3b_004; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$1` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.740808968994; collision_stage3a=stage3a_004; collision_stage3b=stage3b_004; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$1` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.740808968994; collision_stage3a=stage3a_004; collision_stage3b=stage3b_004; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$1` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.740808968994; collision_stage3a=stage3a_004; collision_stage3b=stage3b_004; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$1` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.740808968994; collision_stage3a=stage3a_004; collision_stage3b=stage3b_004; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$2` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.745417752082; collision_stage3a=stage3a_005; collision_stage3b=stage3b_005; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$2` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.745417752082; collision_stage3a=stage3a_005; collision_stage3b=stage3b_005; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$2` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.745417752082; collision_stage3a=stage3a_005; collision_stage3b=stage3b_005; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$2` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.745417752082; collision_stage3a=stage3a_005; collision_stage3b=stage3b_005; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$2` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=3; body_evidence_summary=`invoke invoke jump`
stage3a_stage3b_cosine=0.745417752082; collision_stage3a=stage3a_005; collision_stage3b=stage3b_005; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$3` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=8; body_evidence_summary=`invoke val cl invoke jump branch val cl`
stage3a_stage3b_cosine=0.723697657125; collision_stage3a=stage3a_006; collision_stage3b=stage3b_006; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$3` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=8; body_evidence_summary=`invoke val cl invoke jump branch val cl`
stage3a_stage3b_cosine=0.723697657125; collision_stage3a=stage3a_006; collision_stage3b=stage3b_006; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$3` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=8; body_evidence_summary=`invoke val cl invoke jump branch val cl`
stage3a_stage3b_cosine=0.723697657125; collision_stage3a=stage3a_006; collision_stage3b=stage3b_006; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$3` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=8; body_evidence_summary=`invoke val cl invoke jump branch val cl`
stage3a_stage3b_cosine=0.723697657125; collision_stage3a=stage3a_006; collision_stage3b=stage3b_006; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$3` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=8; body_evidence_summary=`invoke val cl invoke jump branch val cl`
stage3a_stage3b_cosine=0.723697657125; collision_stage3a=stage3a_006; collision_stage3b=stage3b_006; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$4` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=9; body_evidence_summary=`invoke val prop name property invoke val prop name`
stage3a_stage3b_cosine=0.729607381609; collision_stage3a=stage3a_007; collision_stage3b=stage3b_007; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$4` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=9; body_evidence_summary=`invoke val prop name property invoke val prop name`
stage3a_stage3b_cosine=0.729607381609; collision_stage3a=stage3a_007; collision_stage3b=stage3b_007; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$4` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=9; body_evidence_summary=`invoke val prop name property invoke val prop name`
stage3a_stage3b_cosine=0.729607381609; collision_stage3a=stage3a_007; collision_stage3b=stage3b_007; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$4` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=9; body_evidence_summary=`invoke val prop name property invoke val prop name`
stage3a_stage3b_cosine=0.729607381609; collision_stage3a=stage3a_007; collision_stage3b=stage3b_007; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$4` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=9; body_evidence_summary=`invoke val prop name property invoke val prop name`
stage3a_stage3b_cosine=0.729607381609; collision_stage3a=stage3a_007; collision_stage3b=stage3b_007; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$5` — xerces_duplicate_text_group
declaration_tokens=16; body_tokens=7; body_evidence_summary=`invoke val file create invoke val file`
stage3a_stage3b_cosine=0.708750497333; collision_stage3a=stage3a_008; collision_stage3b=stage3b_008; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$5` — xerces_duplicate_text_group
declaration_tokens=16; body_tokens=7; body_evidence_summary=`invoke val file create invoke val file`
stage3a_stage3b_cosine=0.708750497333; collision_stage3a=stage3a_008; collision_stage3b=stage3b_008; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$5` — xerces_duplicate_text_group
declaration_tokens=16; body_tokens=7; body_evidence_summary=`invoke val file create invoke val file`
stage3a_stage3b_cosine=0.708750497333; collision_stage3a=stage3a_008; collision_stage3b=stage3b_008; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$5` — xerces_duplicate_text_group
declaration_tokens=16; body_tokens=7; body_evidence_summary=`invoke val file create invoke val file`
stage3a_stage3b_cosine=0.708750497333; collision_stage3a=stage3a_008; collision_stage3b=stage3b_008; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$5` — xerces_duplicate_text_group
declaration_tokens=16; body_tokens=7; body_evidence_summary=`invoke val file create invoke val file`
stage3a_stage3b_cosine=0.708750497333; collision_stage3a=stage3a_008; collision_stage3b=stage3b_008; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$6` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=10; body_evidence_summary=`invoke val cl name branch jump invoke val cl name`
stage3a_stage3b_cosine=0.729208200033; collision_stage3a=stage3a_009; collision_stage3b=stage3b_009; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$6` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=10; body_evidence_summary=`invoke val cl name branch jump invoke val cl name`
stage3a_stage3b_cosine=0.729208200033; collision_stage3a=stage3a_009; collision_stage3b=stage3b_009; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$6` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=10; body_evidence_summary=`invoke val cl name branch jump invoke val cl name`
stage3a_stage3b_cosine=0.729208200033; collision_stage3a=stage3a_009; collision_stage3b=stage3b_009; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$6` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=10; body_evidence_summary=`invoke val cl name branch jump invoke val cl name`
stage3a_stage3b_cosine=0.729208200033; collision_stage3a=stage3a_009; collision_stage3b=stage3b_009; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$6` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=10; body_evidence_summary=`invoke val cl name branch jump invoke val cl name`
stage3a_stage3b_cosine=0.729208200033; collision_stage3a=stage3a_009; collision_stage3b=stage3b_009; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$7` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=6; body_evidence_summary=`invoke val invoke branch jump val`
stage3a_stage3b_cosine=0.718877327314; collision_stage3a=stage3a_010; collision_stage3b=stage3b_010; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$7` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=6; body_evidence_summary=`invoke val invoke branch jump val`
stage3a_stage3b_cosine=0.718877327314; collision_stage3a=stage3a_010; collision_stage3b=stage3b_010; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$7` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=6; body_evidence_summary=`invoke val invoke branch jump val`
stage3a_stage3b_cosine=0.718877327314; collision_stage3a=stage3a_010; collision_stage3b=stage3b_010; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$7` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=6; body_evidence_summary=`invoke val invoke branch jump val`
stage3a_stage3b_cosine=0.718877327314; collision_stage3a=stage3a_010; collision_stage3b=stage3b_010; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$7` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=6; body_evidence_summary=`invoke val invoke branch jump val`
stage3a_stage3b_cosine=0.718877327314; collision_stage3a=stage3a_010; collision_stage3b=stage3b_010; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.SecuritySupport$8` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=5; body_evidence_summary=`invoke val create invoke val`
stage3a_stage3b_cosine=0.752563426739; collision_stage3a=stage3a_011; collision_stage3b=stage3b_011; body_truncated=0; body_empty=false

### `org.apache.xerces.impl.dv.SecuritySupport$8` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=5; body_evidence_summary=`invoke val create invoke val`
stage3a_stage3b_cosine=0.752563426739; collision_stage3a=stage3a_011; collision_stage3b=stage3b_011; body_truncated=0; body_empty=false

### `org.apache.xerces.parsers.SecuritySupport$8` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=5; body_evidence_summary=`invoke val create invoke val`
stage3a_stage3b_cosine=0.752563426739; collision_stage3a=stage3a_011; collision_stage3b=stage3b_011; body_truncated=0; body_empty=false

### `org.apache.xerces.xinclude.SecuritySupport$8` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=5; body_evidence_summary=`invoke val create invoke val`
stage3a_stage3b_cosine=0.752563426739; collision_stage3a=stage3a_011; collision_stage3b=stage3b_011; body_truncated=0; body_empty=false

### `org.apache.xml.serialize.SecuritySupport$8` — xerces_duplicate_text_group
declaration_tokens=15; body_tokens=5; body_evidence_summary=`invoke val create invoke val`
stage3a_stage3b_cosine=0.752563426739; collision_stage3a=stage3a_011; collision_stage3b=stage3b_011; body_truncated=0; body_empty=false

### `org.apache.xerces.dom.CoreDocumentImpl` — body_truncated
declaration_tokens=998; body_tokens=256; body_evidence_summary=`create kid ok invoke invoke dom normalizer configuration path evaluator changes error checking xml version changed document number node counter xml11 owner allow grammar access append child branch jump create owner document dom exception wr`
stage3a_stage3b_cosine=0.867571169279; collision_stage3a=none; collision_stage3b=none; body_truncated=1; body_empty=false

### `org.apache.xerces.impl.dv.xs.XSSimpleTypeDecl` — body_truncated
declaration_tokens=789; body_tokens=256; body_evidence_summary=`create invoke vs dv normalize type special pattern string ws facet empty context any simple atomic dummy none nmtoken name nc preserve replace collapse invoke vs immutable set variety validation dv facets defined fixed facet white space len`
stage3a_stage3b_cosine=0.858351262421; collision_stage3a=none; collision_stage3b=none; body_truncated=342; body_empty=false

### `org.apache.xerces.impl.xpath.regex.Token` — body_truncated
declaration_tokens=381; body_tokens=256; body_evidence_summary=`newarray create invoke tokens token empty linebeginning linebeginning2 lineend stringbeginning stringend stringend2 wordedge not wordbeginning wordend dot wordchars spaces categories categories2 category names block non bmp ranges nonxs gra`
stage3a_stage3b_cosine=0.78693623906; collision_stage3a=none; collision_stage3b=none; body_truncated=44; body_empty=false

### `org.apache.xerces.impl.xs.XMLSchemaValidator` — body_truncated
declaration_tokens=732; body_tokens=256; body_evidence_summary=`create invoke recognized features feature defaults properties property sg xsi type nil schemalocation nonamespaceschemalocation empty table facet checking invoke create current psvi augmentations dynamic validation schema full normalize dat`
stage3a_stage3b_cosine=0.928750830597; collision_stage3a=none; collision_stage3b=none; body_truncated=125; body_empty=false

### `org.apache.xerces.impl.xs.traversers.XSDHandler` — body_truncated
declaration_tokens=1501; body_tokens=256; body_evidence_summary=`newarray create invoke empty table ns error codes ele comp type circular src include redefine target namespace schema reference attribute declaration group element constraint notation definition internal props correct mg st invoke create no`
stage3a_stage3b_cosine=0.85261623848; collision_stage3a=none; collision_stage3b=none; body_truncated=134; body_empty=false

### `org.apache.xerces.util.EncodingMap` — body_truncated
declaration_tokens=70; body_tokens=256; body_evidence_summary=`put create invoke iana2 java map java2 iana big5 csbig5 cp037 ibm037 csibm037 ebcdic cp us ca nl wt ibm273 cp273 csibm273 ibm277 cp277 csibm277 dk no ibm278 cp278 csibm278 fi se ibm280 cp280 csibm280 ibm284 cp284 csibm284 es gb cp285 ibm285`
stage3a_stage3b_cosine=0.785302479447; collision_stage3a=none; collision_stage3b=none; body_truncated=34; body_empty=false

### `org.apache.xerces.xinclude.XIncludeHandler` — body_truncated
declaration_tokens=1159; body_tokens=256; body_evidence_summary=`invoke create measure branch jump xinclude ns uri include fallback parse xml text attr href encoding accept language included base prefix qname lang xmlns recognized features feature defaults properties property need escaping after escaping`
stage3a_stage3b_cosine=0.849128728579; collision_stage3a=none; collision_stage3b=none; body_truncated=73; body_empty=false

### `org.apache.xerces.dom.DeferredNode` — empty_body_fixed_sample
declaration_tokens=13; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.858485220193; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.apache.xerces.dom3.as.ASAttributeDeclaration` — empty_body_fixed_sample
declaration_tokens=78; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.925097684533; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.apache.xerces.dom3.as.ASContentModel` — empty_body_fixed_sample
declaration_tokens=93; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.92545140518; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.apache.xerces.dom3.as.ASDataType` — empty_body_fixed_sample
declaration_tokens=11; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.82236885175; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true

### `org.apache.xerces.dom3.as.ASElementDeclaration` — empty_body_fixed_sample
declaration_tokens=145; body_tokens=0; body_evidence_summary=`<EMPTY>`
stage3a_stage3b_cosine=0.939673496566; collision_stage3a=none; collision_stage3b=none; body_truncated=0; body_empty=true
