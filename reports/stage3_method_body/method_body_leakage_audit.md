# Method-body leakage audit

The automated checks inspect the decoded `semantic_text` field only.
The fixed manual sample was selected before inspection as: first three sorted class IDs, all classes in prior Stage 3A collision groups, the maximum-total-token class, the first empty-body class, then every `floor(class_count/10)`-th sorted class, retaining the first ten distinct classes.

No embedding, graph, optimization, or downstream result was inspected.

## Automated result

* Checked 11583 subject/class/check combinations.
* Failures: 0.

## Manual sample: jpetstore

### `org.mybatis.jpetstore.domain.Account`
Tokens: declaration=207, body=45, total=265; body_empty=false

```text
[DECLARATION]
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
[METHOD_BODY]
invoke address1 address2 banner name city country email favourite category id first name language preference last password phone state status username zip banner option list option address1 address2 city country email favourite category id first language preference last list password phone state status username zip
```

### `org.mybatis.jpetstore.domain.Cart`
Tokens: declaration=75, body=37, total=121; body_empty=false

```text
[DECLARATION]
public class Cart implements Serializable {
    void addItem(Item, boolean);
    boolean containsItemId(String);
    Iterator getAllCartItems();
    List getCartItemList();
    Iterator getCartItems();
    int getNumberOfItems();
    BigDecimal getSubTotal();
    void incrementQuantityByItemId(String);
    Item removeItemById(String);
    void setQuantityByItemId(String, int);
}
[METHOD_BODY]
invoke create item map list add item increment quantity invoke branch jump create map list contains id key all cart items iterator cart items iterator number size sub total reduce zero increment quantity id remove branch jump
```

### `org.mybatis.jpetstore.domain.CartItem`
Tokens: declaration=55, body=13, total=77; body_empty=false

```text
[DECLARATION]
public class CartItem implements Serializable {
    void calculateTotal();
    Item getItem();
    int getQuantity();
    BigDecimal getTotal();
    void incrementQuantity();
    boolean isInStock();
    void setInStock(boolean);
    void setItem(Item);
    void setQuantity(int);
}
[METHOD_BODY]
invoke calculate total invoke item item quantity total increment quantity calculate stock stock
```

### `org.mybatis.jpetstore.domain.Order`
Tokens: declaration=386, body=67, total=466; body_empty=false

```text
[DECLARATION]
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
[METHOD_BODY]
invoke create line items add line item create invoke items add item bill address1 bill address2 city country state first name last name zip card type courier credit card expiry date locale order date order id ship address1 ship address2 city country state first last zip status total price username has next branch jump username total price credit expiry type courier locale status visa ups ca id
```

### `org.mybatis.jpetstore.mapper.AccountMapper`
Tokens: declaration=61, body=0, total=72; body_empty=true

```text
[DECLARATION]
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
[METHOD_BODY]
<EMPTY>
```

### `org.mybatis.jpetstore.domain.Item`
Tokens: declaration=155, body=37, total=211; body_empty=false

```text
[DECLARATION]
public class Item implements Serializable {
    String getAttribute1();
    String getAttribute2();
    String getAttribute3();
    String getAttribute4();
    String getAttribute5();
    String getItemId();
    BigDecimal getListPrice();
    Product getProduct();
    int getQuantity();
    String getStatus();
    int getSupplierId();
    BigDecimal getUnitCost();
    void setAttribute1(String);
    void setAttribute2(String);
    void setAttribute3(String);
    void setAttribute4(String);
    void setAttribute5(String);
    void setItemId(String);
    void setListPrice(BigDecimal);
    void setProduct(Product);
    void setQuantity(int);
    void setStatus(String);
    void setSupplierId(int);
    void setUnitCost(BigDecimal);
    String toString();
}
[METHOD_BODY]
invoke attribute1 attribute2 attribute3 attribute4 attribute5 item id list price product quantity status supplier id unit cost attribute1 attribute2 attribute3 attribute4 attribute5 item trim invoke list price product quantity status supplier unit cost string make concat constants
```

### `org.mybatis.jpetstore.domain.Sequence`
Tokens: declaration=28, body=8, total=45; body_empty=false

```text
[DECLARATION]
public class Sequence implements Serializable {
    String getName();
    int getNextId();
    void setName(String);
    void setNextId(int);
}
[METHOD_BODY]
invoke invoke name next id name next id
```

### `org.mybatis.jpetstore.mapper.CategoryMapper`
Tokens: declaration=16, body=0, total=27; body_empty=true

```text
[DECLARATION]
public interface CategoryMapper {
    Category getCategory(String);
    List getCategoryList();
}
[METHOD_BODY]
<EMPTY>
```

### `org.mybatis.jpetstore.mapper.LineItemMapper`
Tokens: declaration=24, body=0, total=35; body_empty=true

```text
[DECLARATION]
public interface LineItemMapper {
    List getLineItemsByOrderId(int);
    void insertLineItem(LineItem);
}
[METHOD_BODY]
<EMPTY>
```

### `org.mybatis.jpetstore.mapper.ProductMapper`
Tokens: declaration=26, body=0, total=37; body_empty=true

```text
[DECLARATION]
public interface ProductMapper {
    Product getProduct(String);
    List getProductListByCategory(String);
    List searchProductList(String);
}
[METHOD_BODY]
<EMPTY>
```

## Manual sample: daytrader

### `com.ibm.websphere.samples.daytrader.TradeAction`
Tokens: declaration=264, body=102, total=383; body_empty=false

```text
[DECLARATION]
public class TradeAction implements TradeServices {
    OrderDataBean buy(String, String, double, int);
    void cancelOrder(Integer, boolean);
    OrderDataBean completeOrder(Integer, boolean);
    QuoteDataBean createQuote(String, String, BigDecimal);
    void createTrade();
    AccountDataBean getAccountData(String);
    AccountProfileDataBean getAccountProfileData(String);
    Collection getAllQuotes();
    Collection getClosedOrders(String);
    HoldingDataBean getHolding(Integer);
    Collection getHoldings(String);
    MarketSummaryDataBean getMarketSummary();
    MarketSummaryDataBean getMarketSummaryInternal();
    Collection getOrders(String);
    QuoteDataBean getQuote(String);
    AccountDataBean login(String, String);
    void logout(String);
    void orderCompleted(String, Integer);
    void queueOrder(Integer, boolean);
    AccountDataBean register(String, String, String, String, String, String, BigDecimal);
    AccountDataBean register(String, String, String, String, String, String, String);
    RunStatsDataBean resetTrade(boolean);
    OrderDataBean sell(String, Integer, int);
    OrderDataBean sell(String, int, int);
    AccountProfileDataBean updateAccountProfile(AccountProfileDataBean);
    QuoteDataBean updateQuotePriceVolume(String, BigDecimal, double);
}
[METHOD_BODY]
print trace create invoke branch jump market summary lock next cached msdb trade remote shared cache mode jpa enabled none disabled unable determine create trade invoke branch jump trace buy update quote price volume cancel order unsupported operation exception method not supported complete order unsupported operation exception method not supported quote print remote creation ejb failed direct account data account profile data all quotes closed orders holding holdings market summary cached msdb next lock ejb3 using singleton bean cmp entermonitor exitmonitor internal orders zero primitive workload invalid symbol login logout completed queue register register reset sell sell update price volume cancelled profile
```

### `com.ibm.websphere.samples.daytrader.TradeServices`
Tokens: declaration=216, body=0, total=227; body_empty=true

```text
[DECLARATION]
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
[METHOD_BODY]
<EMPTY>
```

### `com.ibm.websphere.samples.daytrader.beans.MarketSummaryDataBean`
Tokens: declaration=122, body=46, total=182; body_empty=false

```text
[DECLARATION]
public class MarketSummaryDataBean implements Serializable {
    BigDecimal getGainPercent();
    BigDecimal getOpenTSIA();
    MarketSummaryDataBean getRandomInstance();
    Date getSummaryDate();
    BigDecimal getTSIA();
    Collection getTopGainers();
    Collection getTopLosers();
    double getVolume();
    void print();
    void setOpenTSIA(BigDecimal);
    void setSummaryDate(Date);
    void setTSIA(BigDecimal);
    void setTopGainers(Collection);
    void setTopLosers(Collection);
    void setVolume(double);
    String toHTML();
    JsonObject toJSON();
    String toString();
}
[METHOD_BODY]
invoke gain percent compute gain percent invoke create compute branch jump open tsia random instance create branch jump summary date tsia top gainers top losers volume print log open summary date gainers losers volume html current json build gainer stock price change loser string market current
```

### `com.ibm.websphere.samples.daytrader.direct.TradeDirect`
Tokens: declaration=678, body=256, total=975; body_empty=false

```text
[DECLARATION]
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
[METHOD_BODY]
create invoke datasource ds name zero conn count lock initialized invoke branch jump global txn session initialized branch jump global txn session buy create context trade failed queue order committing transaction error rolling back cancel order trade error cancelling cancel update status cancelled check db product name commit complete completing complete completed processing mode exception select orderejb where orderid internal unable find alertcompleted cancelled account id attempt already quote symbol holding buy completing sell sold closed holding data data open quote creating credit account balance close update accountejb set where accountid destroy getting close select accountejb accountid exception getting result set cannot find id login count logout last creation date balance open profile user profile result user passwd full address email credit card all quotes quoteejb closed orders completed conn trace datasource lock connection isolation entermonitor exitmonitor source lookup context ds holdingejb holdingid no results quantity purchase price date symbol holdings holings market summary zero quoteejb change1 desc tsia total volume logging orderejb orderid no results type status completion quantity price fee orders failure could not company volume open1 low high change1 failure statement prepare statement prepare trace factory broker queue streamer topic initializing init login finder passwd cannot incorrect password logging logout out unsupported operation method not supported publish change add suppressed factory streamer topic publishing mdb command company old low high factor shares traded time stock add suppressed broker command neworder two phase direct publish time runtime recreate db tables measure drop thrown executing foll sql register registering release connection failed entermonitor exitmonitor remove
```

### `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean$quotePriceComparator`
Tokens: declaration=21, body=4, total=34; body_empty=false

```text
[DECLARATION]
class TradeSLSBBean$quotePriceComparator implements Comparator {
    int compare(Object, Object);
}
[METHOD_BODY]
invoke compare invoke create
```

### `com.ibm.websphere.samples.daytrader.entities.HoldingDataBean`
Tokens: declaration=138, body=36, total=183; body_empty=false

```text
[DECLARATION]
@Entity
@Table
public class HoldingDataBean implements Serializable {
    boolean equals(Object);
    AccountDataBean getAccount();
    Integer getHoldingID();
    Date getPurchaseDate();
    BigDecimal getPurchasePrice();
    double getQuantity();
    QuoteDataBean getQuote();
    String getQuoteID();
    HoldingDataBean getRandomInstance();
    int hashCode();
    void print();
    void setAccount(AccountDataBean);
    void setHoldingID(Integer);
    void setPurchaseDate(Date);
    void setPurchasePrice(BigDecimal);
    void setQuantity(double);
    void setQuote(QuoteDataBean);
    void setQuoteID(String);
    String toHTML();
    String toString();
}
[METHOD_BODY]
invoke quote invoke quote id branch jump holding id account holding purchase date purchase price quantity symbol branch jump random instance create hash code print log account date price quantity html string create data string data
```

### `com.ibm.websphere.samples.daytrader.util.KeyBlock`
Tokens: declaration=21, body=12, total=42; body_empty=false

```text
[DECLARATION]
public class KeyBlock extends AbstractSequentialList {
    ListIterator listIterator(int);
    int size();
}
[METHOD_BODY]
invoke min max index invoke min max index list iterator create size
```

### `com.ibm.websphere.samples.daytrader.util.TradeConfig`
Tokens: declaration=487, body=205, total=718; body_empty=false

```text
[DECLARATION]
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
[METHOD_BODY]
create invoke order processing mode names access web max users quotes jdbc uid pwd ds name driver needs global transation datasource keyblocksize per page rnd user holdings count id semaphore host random number generator trace action update quote prices prim iterations run publish price change percent sent websocket display alerts use remote ejb market summary interval penny stock recovery miracle multiplier maximum split scenario mixes actions sell deficit ui fee cash one deck card full ejb3 direct sync async phase managed thread standard services jsp images invoke access mode action trace display order alerts hostname error branch jump host name exception getting using localhost jdbc driver needs global transation run max holdings quotes users market summary interval next user id deck string branch jump create card fee compare ignore cash buy sell processing names page web ui percent sent websocket prim iterations publish quote price change random factor one cmpg time time scenario increment count mixes actions deficit entermonitor exitmonitor update prices rnd increment next string semaphore entermonitor exitmonitor number generator address oak st balance big decimal scale credit email com value full value quantity symbol symbols per trade trader config param measure trade setting reverting current set minor exception caughttrying revering use remote ejb
```

### `com.ibm.websphere.samples.daytrader.web.TradeWebContextListener`
Tokens: declaration=33, body=52, total=97; body_empty=false

```text
[DECLARATION]
@WebListener
public class TradeWebContextListener implements ServletContextListener {
    void contextDestroyed(ServletContextEvent);
    void contextInitialized(ServletContextEvent);
}
[METHOD_BODY]
invoke context destroyed trace invoke trade web listener destroy calling context initialized create jump out trade web listener initializing direct settings daytrader runtime mode use remote ejb order processing max users quotes market summary interval prim iterations publish quote price change percent sent websocket display alerts run action trace properties not found
```

### `com.ibm.websphere.samples.daytrader.web.jsf.LoginValidator`
Tokens: declaration=24, body=25, total=58; body_empty=false

```text
[DECLARATION]
@FacesValidator
public class LoginValidator implements Validator {
    void validate(FacesContext, UIComponent, Object);
}
[METHOD_BODY]
compile invoke login regex pattern invoke validate branch jump create pattern matcher severity error validator exception validating submitted login name username validation failed please provide
```

## Manual sample: xerces

### `org.apache.xerces.dom.ASDOMImplementationImpl`
Tokens: declaration=48, body=17, total=76; body_empty=false

```text
[DECLARATION]
public class ASDOMImplementationImpl extends DOMImplementationImpl implements DOMImplementationAS {
    ASModel createAS(boolean);
    DOMASBuilder createDOMASBuilder();
    DOMASWriter createDOMASWriter();
    DOMImplementation getDOMImplementation();
}
[METHOD_BODY]
create invoke singleton invoke create domas builder domas writer dom exception not supported err dom implementation singleton
```

### `org.apache.xerces.dom.ASModelImpl`
Tokens: declaration=319, body=66, total=395; body_empty=false

```text
[DECLARATION]
public class ASModelImpl implements ASModel {
    void addASModel(ASModel);
    ASObject cloneASObject(boolean);
    ASAttributeDeclaration createASAttributeDeclaration(String, String);
    ASContentModel createASContentModel(int, int, short);
    ASElementDeclaration createASElementDeclaration(String, String);
    ASEntityDeclaration createASEntityDeclaration(String);
    ASNotationDeclaration createASNotationDeclaration(String, String, String, String);
    ASObjectList getASModels();
    String getAsHint();
    String getAsLocation();
    short getAsNodeType();
    ASNamedObjectMap getAttributeDeclarations();
    boolean getContainer();
    ASNamedObjectMap getContentModelDeclarations();
    ASNamedObjectMap getElementDeclarations();
    ASNamedObjectMap getEntityDeclarations();
    SchemaGrammar getGrammar();
    Vector getInternalASModels();
    boolean getIsNamespaceAware();
    String getLocalName();
    String getNamespaceURI();
    String getNodeName();
    ASNamedObjectMap getNotationDeclarations();
    ASModel getOwnerASModel();
    String getPrefix();
    short getUsageLocation();
    void importASObject(ASObject);
    void insertASObject(ASObject);
    void removeAS(ASModel);
    void setAsHint(String);
    void setAsLocation(String);
    void setGrammar(SchemaGrammar);
    void setLocalName(String);
    void setNamespaceURI(String);
    void setNodeName(String);
    void setOwnerASModel(ASModel);
    void setPrefix(String);
    boolean validate();
}
[METHOD_BODY]
invoke create namespace aware grammar models invoke create namespace aware grammar models add model element clone object dom exception not supported err attribute declaration dom exception not supported err content model s2 element declaration entity notation hint location node type attribute declarations container branch jump content declarations entity internal name uri node name notation owner prefix usage location object insert remove hint uri owner prefix validate
```

### `org.apache.xerces.dom.AttrImpl`
Tokens: declaration=288, body=118, total=421; body_empty=false

```text
[DECLARATION]
public class AttrImpl extends NodeImpl implements Attr, TypeInfo {
    void checkNormalizationAfterInsert(ChildNode);
    void checkNormalizationAfterRemove(ChildNode);
    Node cloneNode(boolean);
    NodeList getChildNodes();
    Element getElement();
    Node getFirstChild();
    Node getLastChild();
    int getLength();
    String getName();
    String getNodeName();
    short getNodeType();
    String getNodeValue();
    Element getOwnerElement();
    TypeInfo getSchemaTypeInfo();
    boolean getSpecified();
    String getTypeName();
    String getTypeNamespace();
    String getValue();
    boolean hasChildNodes();
    Node insertBefore(Node, Node);
    Node internalInsertBefore(Node, Node, boolean);
    Node internalRemoveChild(Node, boolean);
    boolean isDerivedFrom(String, String, int);
    boolean isEqualNode(Node);
    boolean isId();
    Node item(int);
    ChildNode lastChild();
    void lastChild(ChildNode);
    void makeChildNode();
    void normalize();
    void readObject(ObjectInputStream);
    Node removeChild(Node);
    void rename(String);
    Node replaceChild(Node, Node);
    void setIdAttribute(boolean);
    void setNodeValue(String);
    void setOwnerDocument(CoreDocumentImpl);
    void setReadOnly(boolean, boolean);
    void setSpecified(boolean);
    void setType(Object);
    void setValue(String);
    void synchronizeChildren();
    String toString();
    void writeObject(ObjectOutputStream);
}
[METHOD_BODY]
invoke value has string value invoke name check normalization after insert normalized branch jump next sibling s0 s2 s1 check normalization after remove normalized branch jump next sibling s0 s1 clone node specified child nodes synchronize children element owned owner node first child make last length name synchronize data data type owner element owned schema type info specified namespace string create has nodes insert before internal internal before create error checking previous dom exception hierarchy request err wrong document not found remove error checking previous dom exception not found err derived equal id attribute item last make normalize s2 read object needs sync children rename replace replaced id attribute document read only put identifier needs sync write object
```

### `org.apache.xerces.dom.SecuritySupport$7`
Tokens: declaration=15, body=6, total=30; body_empty=false

```text
[DECLARATION]
class SecuritySupport$7 implements PrivilegedAction {
    Object run();
}
[METHOD_BODY]
invoke val invoke branch jump val
```

### `org.apache.xerces.impl.dv.SecuritySupport$7`
Tokens: declaration=15, body=6, total=30; body_empty=false

```text
[DECLARATION]
class SecuritySupport$7 implements PrivilegedAction {
    Object run();
}
[METHOD_BODY]
invoke val invoke branch jump val
```

### `org.apache.xerces.parsers.SecuritySupport$7`
Tokens: declaration=15, body=6, total=30; body_empty=false

```text
[DECLARATION]
class SecuritySupport$7 implements PrivilegedAction {
    Object run();
}
[METHOD_BODY]
invoke val invoke branch jump val
```

### `org.apache.xerces.xinclude.SecuritySupport$7`
Tokens: declaration=15, body=6, total=30; body_empty=false

```text
[DECLARATION]
class SecuritySupport$7 implements PrivilegedAction {
    Object run();
}
[METHOD_BODY]
invoke val invoke branch jump val
```

### `org.apache.xml.serialize.SecuritySupport$7`
Tokens: declaration=15, body=6, total=30; body_empty=false

```text
[DECLARATION]
class SecuritySupport$7 implements PrivilegedAction {
    Object run();
}
[METHOD_BODY]
invoke val invoke branch jump val
```

### `org.apache.xerces.dom.SecuritySupport$8`
Tokens: declaration=15, body=5, total=29; body_empty=false

```text
[DECLARATION]
class SecuritySupport$8 implements PrivilegedAction {
    Object run();
}
[METHOD_BODY]
invoke val create invoke val
```

### `org.apache.xerces.impl.dv.SecuritySupport$8`
Tokens: declaration=15, body=5, total=29; body_empty=false

```text
[DECLARATION]
class SecuritySupport$8 implements PrivilegedAction {
    Object run();
}
[METHOD_BODY]
invoke val create invoke val
```
