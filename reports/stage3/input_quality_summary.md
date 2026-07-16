# Stage 3 Semantic Input Quality Summary

Tokenizer counting used `nomic-ai/nomic-embed-code` at revision `9a0457648f060c4279d4a3982d2d27a4df6fac59` with `model_max_length=32768`, `truncation=false`, and `add_special_tokens=true`. No generic tokenizer was used. Truncation was applied before this report; the fixed CSV records every dropped method in `truncated_method_count`.

## 1. Summary

| subject | classes | zero-method classes | mean/max methods | mean/max text chars | mean/max token count | truncated classes | total truncated methods |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jpetstore | 24 | 0 | 11.79/57 | 399.00/1752 | 78.46/386 | 0 | 0 |
| daytrader | 53 | 2 | 14.13/70 | 567.85/3368 | 116.08/678 | 0 | 0 |
| xerces-j | 814 | 60 | 9.06/125 | 412.04/6960 | 86.16/1501 | 0 | 0 |

## 2. Truncation risk

### jpetstore
No class exceeded 80% of the 32768-token limit.

### daytrader
No class exceeded 80% of the 32768-token limit.

### xerces-j
No class exceeded 80% of the 32768-token limit.

## 3. Getter/setter saturation diagnosis

No filtering was applied.

### jpetstore
| class_id | method_count | getter/setter count | ratio |
| --- | ---: | ---: | ---: |
| `org.mybatis.jpetstore.domain.Order` | 57 | 54 | 0.947 |
| `org.mybatis.jpetstore.domain.Account` | 36 | 36 | 1.000 |
| `org.mybatis.jpetstore.web.actions.CatalogActionBean` | 26 | 20 | 0.769 |
| `org.mybatis.jpetstore.domain.Item` | 25 | 24 | 0.960 |
| `org.mybatis.jpetstore.web.actions.AccountActionBean` | 18 | 10 | 0.556 |
| `org.mybatis.jpetstore.web.actions.OrderActionBean` | 15 | 10 | 0.667 |
| `org.mybatis.jpetstore.domain.LineItem` | 14 | 13 | 0.929 |
| `org.mybatis.jpetstore.domain.Cart` | 10 | 6 | 0.600 |
| `org.mybatis.jpetstore.domain.CartItem` | 9 | 7 | 0.778 |
| `org.mybatis.jpetstore.domain.Product` | 9 | 8 | 0.889 |

### daytrader
| class_id | method_count | getter/setter count | ratio |
| --- | ---: | ---: | ---: |
| `com.ibm.websphere.samples.daytrader.util.TradeConfig` | 70 | 50 | 0.714 |
| `com.ibm.websphere.samples.daytrader.direct.TradeDirect` | 65 | 32 | 0.492 |
| `com.ibm.websphere.samples.daytrader.web.jsf.AccountDataJSF` | 43 | 40 | 0.930 |
| `com.ibm.websphere.samples.daytrader.web.jsf.TradeConfigJSF` | 40 | 35 | 0.875 |
| `com.ibm.websphere.samples.daytrader.entities.OrderDataBean` | 36 | 30 | 0.833 |
| `com.ibm.websphere.samples.daytrader.util.Log` | 34 | 4 | 0.118 |
| `com.ibm.websphere.samples.daytrader.entities.AccountDataBean` | 30 | 23 | 0.767 |
| `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean` | 28 | 9 | 0.321 |
| `com.ibm.websphere.samples.daytrader.TradeAction` | 26 | 10 | 0.385 |
| `com.ibm.websphere.samples.daytrader.beans.RunStatsDataBean` | 25 | 24 | 0.960 |

### xerces-j
| class_id | method_count | getter/setter count | ratio |
| --- | ---: | ---: | ---: |
| `org.apache.xerces.dom.CoreDocumentImpl` | 125 | 56 | 0.448 |
| `org.apache.xerces.impl.xs.traversers.XSDHandler` | 118 | 28 | 0.237 |
| `org.apache.xerces.xinclude.XIncludeHandler` | 116 | 43 | 0.371 |
| `org.apache.xerces.impl.dtd.DTDGrammar` | 101 | 39 | 0.386 |
| `org.apache.xerces.impl.dv.xs.XSSimpleTypeDecl` | 85 | 63 | 0.741 |
| `org.apache.xerces.dom.NodeImpl` | 82 | 50 | 0.610 |
| `org.apache.xerces.dom.DeferredDocumentImpl` | 77 | 43 | 0.558 |
| `org.apache.xerces.impl.xs.SchemaGrammar` | 74 | 42 | 0.568 |
| `org.apache.xerces.jaxp.datatype.XMLGregorianCalendarImpl` | 64 | 30 | 0.469 |
| `org.apache.xerces.impl.xs.XMLSchemaValidator` | 63 | 16 | 0.254 |

## 4. Contamination checks on decoded `semantic_text` only

### jpetstore
- FQN pattern hits: `0` (must be zero)
- Path separator hits: `0` (must be zero)
- Edge notation hits: `0` (must be zero)
- Label-word hits for manual review:
  - `org.mybatis.jpetstore.domain.Account`: reference

### daytrader
- FQN pattern hits: `0` (must be zero)
- Path separator hits: `0` (must be zero)
- Edge notation hits: `0` (must be zero)
- Label-word hits for manual review: none

### xerces-j
- FQN pattern hits: `0` (must be zero)
- Path separator hits: `0` (must be zero)
- Edge notation hits: `0` (must be zero)
- Label-word hits for manual review:
  - `org.apache.xerces.dom.CoreDocumentImpl`: reference
  - `org.apache.xerces.dom.DeferredDocumentImpl`: reference
  - `org.apache.xerces.dom.DeferredEntityReferenceImpl`: reference
  - `org.apache.xerces.dom.DocumentImpl`: reference
  - `org.apache.xerces.dom.EntityReferenceImpl`: reference
  - `org.apache.xerces.dom.NodeIteratorImpl`: reference
  - `org.apache.xerces.dom.TreeWalkerImpl`: reference
  - `org.apache.xerces.impl.XMLDocumentFragmentScannerImpl`: reference
  - `org.apache.xerces.impl.XMLEntityManager`: reference
  - `org.apache.xerces.impl.XMLScanner`: reference
  - `org.apache.xerces.impl.xpath.regex.Op`: reference
  - `org.apache.xerces.impl.xpath.regex.ParserForXMLSchema`: reference
  - `org.apache.xerces.impl.xpath.regex.RegexParser`: reference
  - `org.apache.xerces.impl.xpath.regex.RegexParser$ReferencePosition`: reference
  - `org.apache.xerces.impl.xpath.regex.Token`: reference
  - `org.apache.xerces.impl.xpath.regex.Token$StringToken`: reference
  - `org.apache.xerces.impl.xs.opti.DefaultDocument`: reference
  - `org.apache.xerces.jaxp.validation.SoftReferenceGrammarPool`: reference
  - `org.apache.xerces.jaxp.validation.SoftReferenceGrammarPool$Entry`: reference
  - `org.apache.xerces.jaxp.validation.SoftReferenceGrammarPool$SoftGrammarReference`: reference
  - `org.apache.xerces.jaxp.validation.StAXDocumentHandler`: reference
  - `org.apache.xerces.jaxp.validation.StAXEventResultBuilder`: reference
  - `org.apache.xerces.jaxp.validation.StAXStreamResultBuilder`: reference
  - `org.apache.xerces.jaxp.validation.WeakReferenceXMLSchema`: reference
  - `org.apache.xerces.parsers.AbstractDOMParser`: reference
  - `org.apache.xerces.parsers.SoftReferenceSymbolTableConfiguration`: reference
  - `org.apache.xerces.stax.XMLEventFactoryImpl`: reference
  - `org.apache.xerces.stax.events.EntityReferenceImpl`: reference
  - `org.apache.xerces.stax.events.XMLEventImpl`: reference
  - `org.apache.xerces.util.SoftReferenceSymbolTable`: reference
  - `org.apache.xerces.util.SoftReferenceSymbolTable$SREntry`: reference
  - `org.apache.xerces.util.SoftReferenceSymbolTable$SREntryData`: reference
  - `org.apache.xerces.util.URI`: reference

## 5. Zero-method classes

### jpetstore
None.
### daytrader
All listed rows use the frozen non-empty empty-body template (header, no method lines, closing brace, final newline).

#### `com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage`
```text
@Qualifier
@Retention
@Target
public interface WebSocketJMSMessage extends Annotation {
}
```

#### `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage$1`
```text
class ActionMessage$1 {
}
```

### xerces-j
All listed rows use the frozen non-empty empty-body template (header, no method lines, closing brace, final newline).

#### `org.apache.xerces.dom.CoreDOMImplementationImpl$RevalidationHandlerHolder`
```text
class CoreDOMImplementationImpl$RevalidationHandlerHolder {
}
```

#### `org.apache.xerces.dom.CoreDOMImplementationImpl$XMLDTDLoaderHolder`
```text
class CoreDOMImplementationImpl$XMLDTDLoaderHolder {
}
```

#### `org.apache.xerces.dom.DeferredDocumentImpl$RefCount`
```text
class DeferredDocumentImpl$RefCount {
}
```

#### `org.apache.xerces.dom.DocumentImpl$EnclosingAttr`
```text
class DocumentImpl$EnclosingAttr implements Serializable {
}
```

#### `org.apache.xerces.dom.DocumentImpl$LEntry`
```text
class DocumentImpl$LEntry implements Serializable {
}
```

#### `org.apache.xerces.dom.NodeListCache`
```text
class NodeListCache implements Serializable {
}
```

#### `org.apache.xerces.dom.ParentNode$UserDataRecord`
```text
class ParentNode$UserDataRecord implements Serializable {
}
```

#### `org.apache.xerces.dom.RangeExceptionImpl`
```text
public class RangeExceptionImpl extends RangeException {
}
```

#### `org.apache.xerces.dom3.as.DOMASException`
```text
public class DOMASException extends RuntimeException {
}
```

#### `org.apache.xerces.impl.XMLEntityManager$CharacterBuffer`
```text
class XMLEntityManager$CharacterBuffer {
}
```

#### `org.apache.xerces.impl.XMLEntityManager$EncodingInfo`
```text
class XMLEntityManager$EncodingInfo {
}
```

#### `org.apache.xerces.impl.dtd.DTDGrammar$ChildrenList`
```text
class DTDGrammar$ChildrenList {
}
```

#### `org.apache.xerces.impl.dv.DVFactoryException`
```text
public class DVFactoryException extends RuntimeException {
}
```

#### `org.apache.xerces.impl.dv.InvalidDatatypeFacetException`
```text
public class InvalidDatatypeFacetException extends DatatypeException {
}
```

#### `org.apache.xerces.impl.dv.InvalidDatatypeValueException`
```text
public class InvalidDatatypeValueException extends DatatypeException {
}
```

#### `org.apache.xerces.impl.dv.xs.SchemaDateTimeException`
```text
public class SchemaDateTimeException extends RuntimeException {
}
```

#### `org.apache.xerces.impl.xpath.regex.Op$ConditionOp`
```text
class Op$ConditionOp extends Op {
}
```

#### `org.apache.xerces.impl.xpath.regex.RegexParser$ReferencePosition`
```text
class RegexParser$ReferencePosition {
}
```

#### `org.apache.xerces.impl.xpath.regex.Token$FixedStringContainer`
```text
class Token$FixedStringContainer {
}
```

#### `org.apache.xerces.impl.xs.SchemaSymbols`
```text
public class SchemaSymbols {
}
```

#### `org.apache.xerces.impl.xs.SubstitutionGroupHandler$OneSubGroup`
```text
class SubstitutionGroupHandler$OneSubGroup {
}
```

#### `org.apache.xerces.impl.xs.identity.UniqueOrKey`
```text
public class UniqueOrKey extends IdentityConstraint {
}
```

#### `org.apache.xerces.impl.xs.traversers.OneAttr`
```text
class OneAttr {
}
```

#### `org.apache.xerces.impl.xs.traversers.XSAnnotationInfo`
```text
class XSAnnotationInfo {
}
```

#### `org.apache.xerces.impl.xs.traversers.XSDAbstractTraverser$FacetInfo`
```text
class XSDAbstractTraverser$FacetInfo {
}
```

#### `org.apache.xerces.impl.xs.traversers.XSDComplexTypeTraverser$ComplexTypeRecoverableError`
```text
class XSDComplexTypeTraverser$ComplexTypeRecoverableError extends Exception {
}
```

#### `org.apache.xerces.impl.xs.traversers.XSDHandler$1`
```text
class XSDHandler$1 {
}
```

#### `org.apache.xerces.jaxp.JAXPConstants`
```text
public interface JAXPConstants {
}
```

#### `org.apache.xerces.jaxp.datatype.XMLGregorianCalendarImpl$1`
```text
class XMLGregorianCalendarImpl$1 {
}
```

#### `org.apache.xerces.jaxp.datatype.XMLGregorianCalendarImpl$DaysInMonth`
```text
class XMLGregorianCalendarImpl$DaysInMonth {
}
```

#### `org.apache.xerces.jaxp.validation.SoftReferenceGrammarPool$SoftGrammarReference`
```text
class SoftReferenceGrammarPool$SoftGrammarReference extends SoftReference {
}
```

#### `org.apache.xerces.jaxp.validation.ValidatorHandlerImpl$1`
```text
class ValidatorHandlerImpl$1 {
}
```

#### `org.apache.xerces.parsers.DOMParserImpl$1`
```text
class DOMParserImpl$1 {
}
```

#### `org.apache.xerces.parsers.SAXParser`
```text
public class SAXParser extends AbstractSAXParser {
}
```

#### `org.apache.xerces.parsers.SecurityConfiguration`
```text
public class SecurityConfiguration extends XIncludeAwareParserConfiguration {
}
```

#### `org.apache.xerces.parsers.SoftReferenceSymbolTableConfiguration`
```text
public class SoftReferenceSymbolTableConfiguration extends XIncludeAwareParserConfiguration {
}
```

#### `org.apache.xerces.parsers.XML11Configurable`
```text
public interface XML11Configurable {
}
```

#### `org.apache.xerces.parsers.XMLDocumentParser`
```text
public class XMLDocumentParser extends AbstractXMLDocumentParser {
}
```

#### `org.apache.xerces.parsers.XMLGrammarParser`
```text
public abstract class XMLGrammarParser extends XMLParser {
}
```

#### `org.apache.xerces.parsers.XMLGrammarPreparser$XMLGrammarLoaderContainer`
```text
class XMLGrammarPreparser$XMLGrammarLoaderContainer {
}
```

#### `org.apache.xerces.util.DOMUtil$ThrowableMethods`
```text
class DOMUtil$ThrowableMethods {
}
```

#### `org.apache.xerces.util.SoftReferenceSymbolTable$SREntryData`
```text
public class SoftReferenceSymbolTable$SREntryData {
}
```

#### `org.apache.xerces.util.SymbolTable$Entry`
```text
public class SymbolTable$Entry {
}
```

#### `org.apache.xerces.util.URI$MalformedURIException`
```text
public class URI$MalformedURIException extends IOException {
}
```

#### `org.apache.xerces.util.XMLAttributesImpl$Attribute`
```text
class XMLAttributesImpl$Attribute {
}
```

#### `org.apache.xerces.util.XMLSymbols`
```text
public class XMLSymbols {
}
```

#### `org.apache.xerces.xni.parser.XMLDTDContentModelFilter`
```text
public interface XMLDTDContentModelFilter extends XMLDTDContentModelHandler, XMLDTDContentModelSource {
}
```

#### `org.apache.xerces.xni.parser.XMLDTDFilter`
```text
public interface XMLDTDFilter extends XMLDTDHandler, XMLDTDSource {
}
```

#### `org.apache.xerces.xni.parser.XMLDocumentFilter`
```text
public interface XMLDocumentFilter extends XMLDocumentHandler, XMLDocumentSource {
}
```

#### `org.apache.xerces.xs.XSConstants`
```text
public interface XSConstants {
}
```

#### `org.apache.xerces.xs.XSException`
```text
public class XSException extends RuntimeException {
}
```

#### `org.apache.xerces.xs.XSTerm`
```text
public interface XSTerm extends XSObject {
}
```

#### `org.apache.xml.serialize.DOMSerializerImpl$DocumentMethods`
```text
class DOMSerializerImpl$DocumentMethods {
}
```

#### `org.apache.xml.serialize.ElementState`
```text
public class ElementState {
}
```

#### `org.apache.xml.serialize.EncodingInfo$CharToByteConverterMethods`
```text
class EncodingInfo$CharToByteConverterMethods {
}
```

#### `org.apache.xml.serialize.EncodingInfo$CharsetMethods`
```text
class EncodingInfo$CharsetMethods {
}
```

#### `org.apache.xml.serialize.LineSeparator`
```text
public class LineSeparator {
}
```

#### `org.apache.xml.serialize.Method`
```text
public class Method {
}
```

#### `org.apache.xml.serialize.OutputFormat$DTD`
```text
public class OutputFormat$DTD {
}
```

#### `org.apache.xml.serialize.OutputFormat$Defaults`
```text
public class OutputFormat$Defaults {
}
```

## 6. Manual review samples

Exactly 10 distinct classes per subject; category order and seed-42 remainder are frozen by the Day 2 procedure.

### jpetstore
### org.mybatis.jpetstore.domain.Order (highest method_count)
kind=class; superclass_present=false; method_count=57; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=006b4b1ce252

```text
public class Order implements Serializable {
    void addLineItem(CartItem);
    void addLineItem(LineItem);
    String getBillAddress1();
    String getBillAddress2();
    String getBillCity();
    String getBillCountry();
    String getBillState();
    String getBillToFirstName();
    String getBillToLastName();
    String getBillZip();
    String getCardType();
    String getCourier();
    String getCreditCard();
    String getExpiryDate();
    List getLineItems();
    String getLocale();
    Date getOrderDate();
    int getOrderId();
    String getShipAddress1();
    String getShipAddress2();
    String getShipCity();
    String getShipCountry();
    String getShipState();
    String getShipToFirstName();
    String getShipToLastName();
    String getShipZip();
    String getStatus();
    BigDecimal getTotalPrice();
    String getUsername();
    void initOrder(Account, Cart);
    void setBillAddress1(String);
    void setBillAddress2(String);
    void setBillCity(String);
    void setBillCountry(String);
    void setBillState(String);
    void setBillToFirstName(String);
    void setBillToLastName(String);
    void setBillZip(String);
    void setCardType(String);
    void setCourier(String);
    void setCreditCard(String);
    void setExpiryDate(String);
    void setLineItems(List);
    void setLocale(String);
    void setOrderDate(Date);
    void setOrderId(int);
    void setShipAddress1(String);
    void setShipAddress2(String);
    void setShipCity(String);
    void setShipCountry(String);
    void setShipState(String);
    void setShipToFirstName(String);
    void setShipToLastName(String);
    void setShipZip(String);
    void setStatus(String);
    void setTotalPrice(BigDecimal);
    void setUsername(String);
}
```
### org.mybatis.jpetstore.domain.Account (highest method_count)
kind=class; superclass_present=false; method_count=36; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=5d95274200b9

```text
public class Account implements Serializable {
    String getAddress1();
    String getAddress2();
    String getBannerName();
    String getCity();
    String getCountry();
    String getEmail();
    String getFavouriteCategoryId();
    String getFirstName();
    String getLanguagePreference();
    String getLastName();
    String getPassword();
    String getPhone();
    String getState();
    String getStatus();
    String getUsername();
    String getZip();
    boolean isBannerOption();
    boolean isListOption();
    void setAddress1(String);
    void setAddress2(String);
    void setBannerName(String);
    void setBannerOption(boolean);
    void setCity(String);
    void setCountry(String);
    void setEmail(String);
    void setFavouriteCategoryId(String);
    void setFirstName(String);
    void setLanguagePreference(String);
    void setLastName(String);
    void setListOption(boolean);
    void setPassword(String);
    void setPhone(String);
    void setState(String);
    void setStatus(String);
    void setUsername(String);
    void setZip(String);
}
```
### org.mybatis.jpetstore.mapper.CategoryMapper (lowest or zero-method)
kind=interface; superclass_present=false; method_count=2; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=77045e6e50f7

```text
public interface CategoryMapper {
    Category getCategory(String);
    List getCategoryList();
}
```
### org.mybatis.jpetstore.mapper.LineItemMapper (lowest or zero-method)
kind=interface; superclass_present=false; method_count=2; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=40f209695f43

```text
public interface LineItemMapper {
    List getLineItemsByOrderId(int);
    void insertLineItem(LineItem);
}
```
### org.mybatis.jpetstore.mapper.AccountMapper (interface)
kind=interface; superclass_present=false; method_count=8; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=fbf942adc8a5

```text
public interface AccountMapper {
    Account getAccountByUsername(String);
    Account getAccountByUsernameAndPassword(String, String);
    void insertAccount(Account);
    void insertProfile(Account);
    void insertSignon(Account);
    void updateAccount(Account);
    void updateProfile(Account);
    void updateSignon(Account);
}
```
### org.mybatis.jpetstore.web.actions.AbstractActionBean (abstract class)
kind=abstract class; superclass_present=false; method_count=3; annotation_count=0; interface_count=2; truncated_method_count=0; input_hash[:12]=32836c8944cd

```text
public abstract class AbstractActionBean implements ActionBean, Serializable {
    ActionBeanContext getContext();
    void setContext(ActionBeanContext);
    void setMessage(String);
}
```
### org.mybatis.jpetstore.service.AccountService (annotated class)
kind=class; superclass_present=false; method_count=4; annotation_count=1; interface_count=0; truncated_method_count=0; input_hash[:12]=425e49393467

```text
@Service
public class AccountService {
    Account getAccount(String);
    Account getAccount(String, String);
    void insertAccount(Account);
    void updateAccount(Account);
}
```
### org.mybatis.jpetstore.web.actions.AccountActionBean (class with superclass)
kind=class; superclass_present=true; method_count=18; annotation_count=1; interface_count=0; truncated_method_count=0; input_hash[:12]=384028f5517a

```text
@SessionScope
public class AccountActionBean extends AbstractActionBean {
    void clear();
    Resolution editAccount();
    Resolution editAccountForm();
    Account getAccount();
    List getCategories();
    List getLanguages();
    List getMyList();
    String getPassword();
    String getUsername();
    boolean isAuthenticated();
    Resolution newAccount();
    Resolution newAccountForm();
    void setMyList(List);
    void setPassword(String);
    void setUsername(String);
    Resolution signoff();
    Resolution signon();
    Resolution signonForm();
}
```
### org.mybatis.jpetstore.mapper.ItemMapper (seed-42 remainder)
kind=interface; superclass_present=false; method_count=4; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=468657031803

```text
public interface ItemMapper {
    int getInventoryQuantity(String);
    Item getItem(String);
    List getItemListByProduct(String);
    void updateInventoryQuantity(Map);
}
```
### org.mybatis.jpetstore.mapper.ProductMapper (seed-42 remainder)
kind=interface; superclass_present=false; method_count=3; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=afd68148ad40

```text
public interface ProductMapper {
    Product getProduct(String);
    List getProductListByCategory(String);
    List searchProductList(String);
}
```

### daytrader
### com.ibm.websphere.samples.daytrader.util.TradeConfig (highest method_count)
kind=class; superclass_present=false; method_count=70; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=e94f37be483c

```text
public class TradeConfig {
    int getAccessMode();
    boolean getActionTrace();
    boolean getDisplayOrderAlerts();
    String getHostname();
    boolean getJDBCDriverNeedsGlobalTransation();
    boolean getLongRun();
    int getMAX_HOLDINGS();
    int getMAX_QUOTES();
    int getMAX_USERS();
    int getMarketSummaryInterval();
    String getNextUserIDFromDeck();
    BigDecimal getOrderFee(String);
    int getOrderProcessingMode();
    String[] getOrderProcessingModeNames();
    String getPage(int);
    int getPercentSentToWebsocket();
    int getPrimIterations();
    boolean getPublishQuotePriceChange();
    BigDecimal getRandomPriceChangeFactor();
    int getRunTimeMode();
    String[] getRunTimeModeNames();
    char getScenarioAction(boolean);
    int getScenarioCount();
    int[][] getScenarioMixes();
    boolean getTrace();
    boolean getUpdateQuotePrices();
    String getUserID();
    int getWebInterface();
    String[] getWebInterfaceNames();
    void incrementScenarioCount();
    void incrementSellDeficit();
    String nextUserID();
    double random();
    String rndAddress();
    String rndBalance();
    BigDecimal rndBigDecimal(float);
    boolean rndBoolean();
    String rndCreditCard();
    String rndEmail(String);
    float rndFloat(int);
    String rndFullName();
    int rndInt(int);
    String rndNewUserID();
    float rndPrice();
    float rndQuantity();
    String rndSymbol();
    String rndSymbols();
    String rndUserID();
    void setAccessMode(int);
    void setActionTrace(boolean);
    void setConfigParam(String, String);
    void setDisplayOrderAlerts(boolean);
    void setJDBCDriverNeedsGlobalTransation(boolean);
    void setLongRun(boolean);
    void setMAX_HOLDINGS(int);
    void setMAX_QUOTES(int);
    void setMAX_USERS(int);
    void setMarketSummaryInterval(int);
    void setOrderProcessingMode(int);
    void setPercentSentToWebsocket(int);
    void setPrimIterations(int);
    void setPublishQuotePriceChange(boolean);
    void setRunTimeMode(int);
    void setRunTimeModeNames(String[]);
    void setScenarioCount(int);
    void setTrace(boolean);
    void setUpdateQuotePrices(boolean);
    void setUseRemoteEJBInterface(boolean);
    void setWebInterface(int);
    boolean useRemoteEJBInterface();
}
```
### com.ibm.websphere.samples.daytrader.direct.TradeDirect (highest method_count)
kind=class; superclass_present=false; method_count=65; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=13e953a2da53

```text
public class TradeDirect implements TradeServices {
    OrderDataBean buy(String, String, double, int);
    void cancelOrder(Connection, Integer);
    void cancelOrder(Integer, boolean);
    String checkDBProductName();
    void commit(Connection);
    OrderDataBean completeOrder(Connection, Integer);
    OrderDataBean completeOrder(Integer, boolean);
    HoldingDataBean createHolding(Connection, int, String, double, BigDecimal);
    OrderDataBean createOrder(Connection, AccountDataBean, QuoteDataBean, HoldingDataBean, String, double);
    QuoteDataBean createQuote(String, String, BigDecimal);
    void creditAccountBalance(Connection, AccountDataBean, BigDecimal);
    void destroy();
    AccountDataBean getAccountData(Connection, String);
    AccountDataBean getAccountData(String);
    AccountDataBean getAccountData(int);
    AccountDataBean getAccountData(int, Connection);
    AccountDataBean getAccountDataFromResultSet(ResultSet);
    AccountProfileDataBean getAccountProfileData(Connection, Integer);
    AccountProfileDataBean getAccountProfileData(Connection, String);
    AccountProfileDataBean getAccountProfileData(String);
    AccountProfileDataBean getAccountProfileDataFromResultSet(ResultSet);
    Collection getAllQuotes();
    Collection getClosedOrders(String);
    Connection getConn();
    Connection getConnPublic();
    void getDataSource();
    HoldingDataBean getHolding(Integer);
    HoldingDataBean getHoldingData(Connection, int);
    HoldingDataBean getHoldingData(int);
    HoldingDataBean getHoldingDataFromResultSet(ResultSet);
    Collection getHoldings(String);
    boolean getInGlobalTxn();
    MarketSummaryDataBean getMarketSummary();
    OrderDataBean getOrderData(Connection, int);
    OrderDataBean getOrderDataFromResultSet(ResultSet);
    Collection getOrders(String);
    QuoteDataBean getQuote(Connection, String);
    QuoteDataBean getQuote(String);
    QuoteDataBean getQuoteData(Connection, String);
    QuoteDataBean getQuoteDataFromResultSet(ResultSet);
    QuoteDataBean getQuoteForUpdate(Connection, String);
    PreparedStatement getStatement(Connection, String);
    PreparedStatement getStatement(Connection, String, int, int);
    void init();
    AccountDataBean login(String, String);
    void logout(String);
    void orderCompleted(String, Integer);
    void publishQuotePriceChange(QuoteDataBean, BigDecimal, BigDecimal, double);
    void queueOrder(Integer, boolean);
    boolean recreateDBTables(Object[], PrintWriter);
    AccountDataBean register(String, String, String, String, String, String, BigDecimal);
    void releaseConn(Connection);
    void removeHolding(Connection, int, int);
    RunStatsDataBean resetTrade(boolean);
    void rollBack(Connection, Exception);
    OrderDataBean sell(String, Integer, int);
    void setInGlobalTxn(boolean);
    AccountProfileDataBean updateAccountProfile(AccountProfileDataBean);
    void updateAccountProfile(Connection, AccountProfileDataBean);
    void updateHoldingStatus(Connection, Integer, String);
    void updateOrderHolding(Connection, int, int);
    void updateOrderStatus(Connection, Integer, String);
    QuoteDataBean updateQuotePriceVolume(String, BigDecimal, double);
    void updateQuotePriceVolume(Connection, String, BigDecimal, double, double);
    QuoteDataBean updateQuotePriceVolumeInt(String, BigDecimal, double, boolean);
}
```
### com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage (lowest or zero-method)
kind=interface; superclass_present=false; method_count=0; annotation_count=3; interface_count=1; truncated_method_count=0; input_hash[:12]=e95b8733d318

```text
@Qualifier
@Retention
@Target
public interface WebSocketJMSMessage extends Annotation {
}
```
### com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage$1 (lowest or zero-method)
kind=class; superclass_present=false; method_count=0; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=57d3596e7f45

```text
class ActionMessage$1 {
}
```
### com.ibm.websphere.samples.daytrader.TradeServices (interface)
kind=interface; superclass_present=false; method_count=22; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=79faebc4f5a7

```text
public interface TradeServices {
    OrderDataBean buy(String, String, double, int);
    void cancelOrder(Integer, boolean);
    OrderDataBean completeOrder(Integer, boolean);
    QuoteDataBean createQuote(String, String, BigDecimal);
    AccountDataBean getAccountData(String);
    AccountProfileDataBean getAccountProfileData(String);
    Collection getAllQuotes();
    Collection getClosedOrders(String);
    HoldingDataBean getHolding(Integer);
    Collection getHoldings(String);
    MarketSummaryDataBean getMarketSummary();
    Collection getOrders(String);
    QuoteDataBean getQuote(String);
    AccountDataBean login(String, String);
    void logout(String);
    void orderCompleted(String, Integer);
    void queueOrder(Integer, boolean);
    AccountDataBean register(String, String, String, String, String, String, BigDecimal);
    RunStatsDataBean resetTrade(boolean);
    OrderDataBean sell(String, Integer, int);
    AccountProfileDataBean updateAccountProfile(AccountProfileDataBean);
    QuoteDataBean updateQuotePriceVolume(String, BigDecimal, double);
}
```
### com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB (annotated class)
kind=class; superclass_present=false; method_count=2; annotation_count=3; interface_count=1; truncated_method_count=0; input_hash[:12]=491238598412

```text
@MessageDriven
@TransactionAttribute
@TransactionManagement
public class DTBroker3MDB implements MessageListener {
    TradeServices getTrade(boolean);
    void onMessage(Message);
}
```
### com.ibm.websphere.samples.daytrader.util.KeyBlock (class with superclass)
kind=class; superclass_present=true; method_count=2; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=64a09d222de4

```text
public class KeyBlock extends AbstractSequentialList {
    ListIterator listIterator(int);
    int size();
}
```
### com.ibm.websphere.samples.daytrader.util.Log (seed-42 remainder)
kind=class; superclass_present=false; method_count=34; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=5c88d85e0f49

```text
public class Log {
    void debug(String);
    boolean doActionTrace();
    boolean doDebug();
    boolean doStat();
    boolean doTrace();
    void error(String);
    void error(String, String, String, Throwable);
    void error(String, String, Throwable);
    void error(String, Throwable);
    void error(Throwable, String);
    void error(Throwable, String, String);
    void error(Throwable, String, String, String);
    boolean getActionTrace();
    boolean getTrace();
    void log(String);
    void log(String, String);
    void log(String, String, String);
    void print(String);
    void printCollection(Collection);
    void printCollection(String, Collection);
    void printObject(Object);
    void setActionTrace(boolean);
    void setTrace(boolean);
    void stat(String);
    void trace(String);
    void trace(String, Object);
    void trace(String, Object, Object);
    void trace(String, Object, Object, Object);
    void trace(String, Object, Object, Object, Object);
    void trace(String, Object, Object, Object, Object, Object);
    void trace(String, Object, Object, Object, Object, Object, Object);
    void trace(String, Object, Object, Object, Object, Object, Object, Object);
    void traceEnter(String);
    void traceExit(String);
}
```
### com.ibm.websphere.samples.daytrader.web.OrdersAlertFilter (seed-42 remainder)
kind=class; superclass_present=false; method_count=3; annotation_count=1; interface_count=1; truncated_method_count=0; input_hash[:12]=92772fd1a525

```text
@WebFilter
public class OrdersAlertFilter implements Filter {
    void destroy();
    void doFilter(ServletRequest, ServletResponse, FilterChain);
    void init(FilterConfig);
}
```
### com.ibm.websphere.samples.daytrader.web.jsf.JSFLoginFilter (seed-42 remainder)
kind=class; superclass_present=false; method_count=3; annotation_count=1; interface_count=1; truncated_method_count=0; input_hash[:12]=215ce11132c1

```text
@WebFilter
public class JSFLoginFilter implements Filter {
    void destroy();
    void doFilter(ServletRequest, ServletResponse, FilterChain);
    void init(FilterConfig);
}
```

### xerces-j
### org.apache.xerces.dom.CoreDocumentImpl (highest method_count)
kind=class; superclass_present=true; method_count=125; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=483a6d2dce2e

```text
public class CoreDocumentImpl extends ParentNode implements Document {
    void abort();
    void addEventListener(NodeImpl, String, EventListener, boolean);
    Node adoptNode(Node);
    void callUserDataHandlers(Node, Node, short);
    void callUserDataHandlers(Node, Node, short, Hashtable);
    boolean canRenameElements(String, String, ElementImpl);
    void changed();
    int changes();
    void checkDOMNSErr(String, String);
    void checkNamespaceWF(String, int, int);
    void checkQName(String, String);
    void clearIdentifiers();
    Object clone();
    Node cloneNode(boolean);
    void cloneNode(CoreDocumentImpl, boolean);
    void copyEventListeners(NodeImpl, NodeImpl);
    Attr createAttribute(String);
    Attr createAttributeNS(String, String);
    Attr createAttributeNS(String, String, String);
    CDATASection createCDATASection(String);
    Comment createComment(String);
    DocumentFragment createDocumentFragment();
    DocumentType createDocumentType(String, String, String);
    Element createElement(String);
    ElementDefinitionImpl createElementDefinition(String);
    Element createElementNS(String, String);
    Element createElementNS(String, String, String);
    Entity createEntity(String);
    EntityReference createEntityReference(String);
    Notation createNotation(String);
    ProcessingInstruction createProcessingInstruction(String, String);
    Text createTextNode(String);
    void deletedText(CharacterDataImpl, int, int);
    boolean dispatchEvent(NodeImpl, Event);
    void freeNodeListCache(NodeListCache);
    boolean getAsync();
    String getBaseURI();
    DocumentType getDoctype();
    Element getDocumentElement();
    String getDocumentURI();
    DOMConfiguration getDomConfig();
    Element getElementById(String);
    NodeList getElementsByTagName(String);
    NodeList getElementsByTagNameNS(String, String);
    String getEncoding();
    boolean getErrorChecking();
    Object getFeature(String, String);
    Element getIdentifier(String);
    Enumeration getIdentifiers();
    DOMImplementation getImplementation();
    String getInputEncoding();
    boolean getMutationEvents();
    NodeListCache getNodeListCache(ParentNode);
    String getNodeName();
    int getNodeNumber();
    int getNodeNumber(Node);
    short getNodeType();
    Document getOwnerDocument();
    boolean getStandalone();
    boolean getStrictErrorChecking();
    String getTextContent();
    Object getUserData(Node, String);
    Object getUserData(NodeImpl);
    Hashtable getUserDataRecord(Node);
    String getVersion();
    String getXmlEncoding();
    boolean getXmlStandalone();
    String getXmlVersion();
    Node importNode(Node, boolean);
    Node importNode(Node, boolean, boolean, HashMap);
    Node insertBefore(Node, Node);
    void insertedNode(NodeImpl, NodeImpl, boolean);
    void insertedText(CharacterDataImpl, int, int);
    void insertingNode(NodeImpl, boolean);
    boolean isKidOK(Node, Node);
    boolean isNormalizeDocRequired();
    boolean isValidQName(String, String, boolean);
    boolean isXML11Version();
    boolean isXMLName(String, boolean);
    boolean isXMLVersionChanged();
    boolean load(String);
    boolean loadXML(String);
    void modifiedAttrValue(AttrImpl, String);
    void modifiedCharacterData(NodeImpl, String, String, boolean);
    void modifyingCharacterData(NodeImpl, boolean);
    void normalizeDocument();
    void putIdentifier(String, Element);
    void readObject(ObjectInputStream);
    Node removeChild(Node);
    void removeEventListener(NodeImpl, String, EventListener, boolean);
    void removeIdentifier(String);
    Hashtable removeUserDataTable(Node);
    void removedAttrNode(AttrImpl, NodeImpl, String);
    void removedNode(NodeImpl, boolean);
    void removingNode(NodeImpl, NodeImpl, boolean);
    Node renameNode(Node, String, String);
    void renamedAttrNode(Attr, Attr);
    void renamedElement(Element, Element);
    Node replaceChild(Node, Node);
    ElementImpl replaceRenameElement(ElementImpl, String, String);
    void replacedCharacterData(NodeImpl, String, String);
    void replacedNode(NodeImpl);
    void replacedText(CharacterDataImpl);
    void replacingData(NodeImpl);
    void replacingNode(NodeImpl);
    String saveXML(Node);
    void setAsync(boolean);
    void setAttrNode(AttrImpl, AttrImpl);
    void setDocumentURI(String);
    void setEncoding(String);
    void setErrorChecking(boolean);
    void setInputEncoding(String);
    void setMutationEvents(boolean);
    void setStandalone(boolean);
    void setStrictErrorChecking(boolean);
    void setTextContent(String);
    Object setUserData(Node, String, Object, UserDataHandler);
    void setUserData(NodeImpl, Object);
    void setUserDataTable(Node, Hashtable);
    void setVersion(String);
    void setXmlEncoding(String);
    void setXmlStandalone(boolean);
    void setXmlVersion(String);
    void undeferChildren(Node);
    void writeObject(ObjectOutputStream);
}
```
### org.apache.xerces.impl.xs.traversers.XSDHandler (highest method_count)
kind=class; superclass_present=false; method_count=118; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=80fc9a7120ba

```text
public class XSDHandler {
    void addGlobalAttributeDecl(XSAttributeDecl);
    void addGlobalAttributeDecls(SchemaGrammar, SchemaGrammar);
    void addGlobalAttributeGroupDecl(XSAttributeGroupDecl);
    void addGlobalAttributeGroupDecls(SchemaGrammar, SchemaGrammar);
    void addGlobalComponent(XSObject, XSDDescription);
    void addGlobalComponents(Vector, Hashtable);
    void addGlobalElementDecl(XSElementDecl);
    void addGlobalElementDecls(SchemaGrammar, SchemaGrammar);
    void addGlobalGroupDecl(XSGroupDecl);
    void addGlobalGroupDecls(SchemaGrammar, SchemaGrammar);
    void addGlobalNotationDecl(XSNotationDecl);
    void addGlobalNotationDecls(SchemaGrammar, SchemaGrammar);
    void addGlobalTypeDecl(XSTypeDefinition);
    void addGlobalTypeDecls(SchemaGrammar, SchemaGrammar);
    void addGrammarComponents(SchemaGrammar, SchemaGrammar);
    void addGrammars(Vector);
    void addIDConstraintDecl(IdentityConstraint);
    void addImportList(SchemaGrammar, Vector, Vector);
    void addNamespaceDependency(String, String, Vector);
    void addNewGrammarComponents(SchemaGrammar, SchemaGrammar);
    void addNewGrammarLocations(SchemaGrammar, SchemaGrammar);
    void addNewImportedGrammars(SchemaGrammar, SchemaGrammar);
    void addRelatedAttribute(XSAttributeDeclaration, Vector, String, Hashtable);
    void addRelatedElement(XSElementDeclaration, Vector, String, Hashtable);
    void addRelatedType(XSTypeDefinition, Vector, String, Hashtable);
    void buildGlobalNameRegistries();
    boolean canAddComponent(XSObject, XSDDescription);
    boolean canAddComponents(Vector);
    int changeRedefineGroup(String, String, String, Element, XSDocumentInfo);
    void checkForDuplicateNames(String, int, Element);
    void checkForDuplicateNames(String, int, Hashtable, Hashtable, Element, XSDocumentInfo);
    XSDocumentInfo constructTrees(Element, String, XSDDescription, boolean);
    boolean containedImportedGrammar(Vector, SchemaGrammar);
    void createAnnotationValidator();
    SchemaGrammar createGrammarFrom(SchemaGrammar);
    void createTraversers();
    String doc2SystemId(Element);
    SimpleLocator element2Locator(Element);
    boolean element2Locator(Element, SimpleLocator);
    String emptyString2Null(String);
    boolean existingGrammars(Vector);
    Vector expandComponents(XSObject[], Hashtable);
    Vector expandGrammars(SchemaGrammar[]);
    void expandImportList(String, Vector);
    void expandRelatedAttributeComponents(XSAttributeDeclaration, Vector, String, Hashtable);
    void expandRelatedAttributeGroupComponents(XSAttributeGroupDefinition, Vector, String, Hashtable);
    void expandRelatedAttributeUseComponents(XSAttributeUse, Vector, String, Hashtable);
    void expandRelatedAttributeUsesComponents(XSObjectList, Vector, String, Hashtable);
    void expandRelatedComplexTypeComponents(XSComplexTypeDecl, Vector, String, Hashtable);
    void expandRelatedComponents(XSObject, Vector, Hashtable);
    void expandRelatedElementComponents(XSElementDeclaration, Vector, String, Hashtable);
    void expandRelatedModelGroupComponents(XSModelGroup, Vector, String, Hashtable);
    void expandRelatedModelGroupDefinitionComponents(XSModelGroupDefinition, Vector, String, Hashtable);
    void expandRelatedParticleComponents(XSParticle, Vector, String, Hashtable);
    void expandRelatedSimpleTypeComponents(XSSimpleTypeDefinition, Vector, String, Hashtable);
    void expandRelatedTypeComponents(XSTypeDefinition, Vector, String, Hashtable);
    void fillInLocalElemInfo(Element, XSDocumentInfo, int, XSObject, XSParticleDecl);
    Vector findDependentNamespaces(String, Hashtable);
    SchemaGrammar findGrammar(XSDDescription, boolean);
    String findQName(String, XSDocumentInfo);
    XSDocumentInfo findXSDocumentForDecl(XSDocumentInfo, Element, XSDocumentInfo);
    XSAttributeDecl getGlobalAttributeDecl(String);
    XSAttributeGroupDecl getGlobalAttributeGroupDecl(String);
    Object getGlobalDecl(String, int);
    Object getGlobalDecl(XSDocumentInfo, int, QName, Element);
    Object getGlobalDeclFromGrammar(SchemaGrammar, int, String);
    Object getGlobalDeclFromGrammar(SchemaGrammar, int, String, String);
    XSElementDecl getGlobalElementDecl(String);
    XSGroupDecl getGlobalGroupDecl(String);
    XSNotationDecl getGlobalNotationDecl(String);
    XSTypeDefinition getGlobalTypeDecl(String);
    SchemaGrammar getGrammar(String);
    Object getGrpOrAttrGrpRedefinedByRestriction(int, QName, XSDocumentInfo, Element);
    IdentityConstraint getIDConstraintDecl(String);
    Hashtable getIDRegistry();
    Hashtable getIDRegistry_sub();
    Element getSchemaDocument(String, DOMInputSource, boolean, short, Element);
    Element getSchemaDocument(String, SAXInputSource, boolean, short, Element);
    Element getSchemaDocument(String, StAXInputSource, boolean, short, Element);
    Element getSchemaDocument(String, XMLInputSource, boolean, short, Element);
    Element getSchemaDocument(XSInputSource, XSDDescription);
    Element getSchemaDocument0(XSDHandler$XSDKey, String, Element);
    Element getSchemaDocument1(boolean, boolean, XMLInputSource, Element, IOException);
    SchemaGrammar getSchemaGrammar(XSDDescription);
    boolean isExistingGrammar(XSDDescription, boolean);
    boolean needReportTNSError(String);
    boolean nonAnnotationContent(Element);
    String null2EmptyString(String);
    SchemaGrammar parseSchema(XMLInputSource, XSDDescription, Hashtable);
    void prepareForParse();
    void prepareForTraverse();
    boolean removeParticle(XSModelGroupImpl, XSParticleDecl);
    void renameRedefiningComponents(XSDocumentInfo, Element, String, String, String);
    void reportSchemaError(String, Object[], Element);
    void reportSchemaError(String, Object[], Element, Exception);
    void reportSchemaWarning(String, Object[], Element);
    void reportSchemaWarning(String, Object[], Element, Exception);
    void reportSharingError(String, String);
    void reset(XMLComponentManager);
    void resolveKeyRefs();
    Element resolveSchema(XMLInputSource, XSDDescription, boolean, Element);
    Element resolveSchema(XSDDescription, boolean, Element, boolean);
    XMLInputSource resolveSchemaSource(XSDDescription, boolean, Element, boolean);
    String schemaDocument2SystemId(XSDocumentInfo);
    void setDVFactory(SchemaDVFactory);
    void setDeclPool(XSDeclarationPool);
    void setGenerateSyntheticAnnotations(boolean);
    void setSchemasVisible(XSDocumentInfo);
    void storeKeyRef(Element, XSDocumentInfo, XSElementDecl);
    Object traverseGlobalDecl(int, Element, XSDocumentInfo, SchemaGrammar);
    void traverseLocalElements();
    void traverseSchemas(ArrayList);
    void updateImportDependencies(Hashtable);
    void updateImportList(SchemaGrammar, Vector, Vector);
    void updateImportList(Vector, Vector);
    void updateImportListFor(SchemaGrammar);
    void updateImportListWith(SchemaGrammar);
    void validateAnnotations(ArrayList);
}
```
### org.apache.xerces.dom.CoreDOMImplementationImpl$RevalidationHandlerHolder (lowest or zero-method)
kind=class; superclass_present=false; method_count=0; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=d4c1e4d22cf6

```text
class CoreDOMImplementationImpl$RevalidationHandlerHolder {
}
```
### org.apache.xerces.dom.CoreDOMImplementationImpl$XMLDTDLoaderHolder (lowest or zero-method)
kind=class; superclass_present=false; method_count=0; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=f263555e81ff

```text
class CoreDOMImplementationImpl$XMLDTDLoaderHolder {
}
```
### org.apache.xerces.dom.DeferredNode (interface)
kind=interface; superclass_present=false; method_count=1; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=90fbbab23e08

```text
public interface DeferredNode extends Node {
    int getNodeIndex();
}
```
### org.apache.xerces.dom.CharacterDataImpl (abstract class)
kind=abstract class; superclass_present=true; method_count=15; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=ff0367dfc193

```text
public abstract class CharacterDataImpl extends ChildNode {
    void appendData(String);
    void deleteData(int, int);
    NodeList getChildNodes();
    String getData();
    int getLength();
    String getNodeValue();
    void insertData(int, String);
    void internalDeleteData(int, int, boolean);
    void internalInsertData(int, String, boolean);
    void replaceData(int, int, String);
    void setData(String);
    void setNodeValue(String);
    void setNodeValueInternal(String);
    void setNodeValueInternal(String, boolean);
    String substringData(int, int);
}
```
### org.apache.xerces.dom.ASDOMImplementationImpl (class with superclass)
kind=class; superclass_present=true; method_count=4; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=7eb08569cb6c

```text
public class ASDOMImplementationImpl extends DOMImplementationImpl implements DOMImplementationAS {
    ASModel createAS(boolean);
    DOMASBuilder createDOMASBuilder();
    DOMASWriter createDOMASWriter();
    DOMImplementation getDOMImplementation();
}
```
### org.apache.xerces.xs.XSAttributeGroupDefinition (seed-42 remainder)
kind=interface; superclass_present=false; method_count=4; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=3a2afd536b74

```text
public interface XSAttributeGroupDefinition extends XSObject {
    XSAnnotation getAnnotation();
    XSObjectList getAnnotations();
    XSObjectList getAttributeUses();
    XSWildcard getAttributeWildcard();
}
```
### org.apache.xerces.xs.ElementPSVI (seed-42 remainder)
kind=interface; superclass_present=false; method_count=4; annotation_count=0; interface_count=1; truncated_method_count=0; input_hash[:12]=bd5984641a6f

```text
public interface ElementPSVI extends ItemPSVI {
    XSElementDeclaration getElementDeclaration();
    boolean getNil();
    XSNotationDeclaration getNotation();
    XSModel getSchemaInformation();
}
```
### org.apache.xerces.parsers.XMLGrammarPreparser$XMLGrammarLoaderContainer (seed-42 remainder)
kind=class; superclass_present=false; method_count=0; annotation_count=0; interface_count=0; truncated_method_count=0; input_hash[:12]=9285916203a7

```text
class XMLGrammarPreparser$XMLGrammarLoaderContainer {
}
```
