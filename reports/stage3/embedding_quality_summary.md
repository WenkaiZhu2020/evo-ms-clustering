# Stage 3 Embedding Quality Summary

This diagnostic report uses only the saved `embeddings.npy`, CSV mapping,
per-class hashes, and saved nearest-neighbour files. It does not load the
Nomic model and does not construct `semantic_edges.csv`.

Tokenizer metadata for token display: `nomic-ai/nomic-embed-code` revision `9a0457648f060c4279d4a3982d2d27a4df6fac59`
with `model_max_length=32768`, `truncation=false`, and special tokens enabled.

## 1. Cross-subject summary

| subject | classes | dimension | min norm | mean norm | max norm | NaN | Inf | all-zero | duplicate semantic_text groups | duplicate embedding groups | min off-diagonal cosine | mean off-diagonal cosine | median off-diagonal cosine | max off-diagonal cosine | mean top-1 | median top-1 | min top-1 | max top-1 | encoding seconds | aggregate embedding SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| jpetstore | 24 | 3584 | 0.999526616 | 1.000096853 | 1.000439267 | 0 | 0 | 0 | 0 | 0 | 0.199783621 | 0.416250244 | 0.347854680 | 0.837673220 | 0.749622413 | 0.767326182 | 0.585185360 | 0.837673220 | 3.107451 | `0ae28938fef7b0c0295a5b1d33527708af7493b4f43d524436ffbf258db8802a` |
| daytrader | 53 | 3584 | 0.999746048 | 1.000005944 | 1.000383103 | 0 | 0 | 0 | 0 | 0 | 0.026817245 | 0.285946636 | 0.244587856 | 0.885107379 | 0.687570978 | 0.715139343 | 0.354437406 | 0.885107379 | 7.387897 | `c7d2cbeec9d4c6ff5f9054b7d66563e98cffc6774771d5727030248299b7756e` |
| xerces | 814 | 3584 | 0.999543728 | 1.000008292 | 1.000469521 | 0 | 0 | 0 | 11 | 11 | -0.010522810 | 0.282221956 | 0.270341977 | 1.000000000 | 0.801170565 | 0.808810076 | 0.418384596 | 1.000000000 | 54.291155 | `9504e21bb305a60cdfce58421b64240d1af893fd549b40b9441a00bf0fee8cb1` |

## 2. Duplicate diagnostics

### jpetstore
Identical text groups:
- None.
Identical saved embedding groups:
- None.

### daytrader
Identical text groups:
- None.
Identical saved embedding groups:
- None.

### xerces
Identical text groups:
- `org.apache.xerces.dom.ObjectFactory`, `org.apache.xerces.impl.dv.ObjectFactory`, `org.apache.xerces.parsers.ObjectFactory`, `org.apache.xerces.xinclude.ObjectFactory`, `org.apache.xml.serialize.ObjectFactory` (same semantic_text)
- `org.apache.xerces.dom.ObjectFactory$ConfigurationError`, `org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError`, `org.apache.xerces.parsers.ObjectFactory$ConfigurationError`, `org.apache.xerces.xinclude.ObjectFactory$ConfigurationError`, `org.apache.xml.serialize.ObjectFactory$ConfigurationError` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport`, `org.apache.xerces.impl.dv.SecuritySupport`, `org.apache.xerces.parsers.SecuritySupport`, `org.apache.xerces.xinclude.SecuritySupport`, `org.apache.xml.serialize.SecuritySupport` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$1`, `org.apache.xerces.impl.dv.SecuritySupport$1`, `org.apache.xerces.parsers.SecuritySupport$1`, `org.apache.xerces.xinclude.SecuritySupport$1`, `org.apache.xml.serialize.SecuritySupport$1` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$2`, `org.apache.xerces.impl.dv.SecuritySupport$2`, `org.apache.xerces.parsers.SecuritySupport$2`, `org.apache.xerces.xinclude.SecuritySupport$2`, `org.apache.xml.serialize.SecuritySupport$2` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$3`, `org.apache.xerces.impl.dv.SecuritySupport$3`, `org.apache.xerces.parsers.SecuritySupport$3`, `org.apache.xerces.xinclude.SecuritySupport$3`, `org.apache.xml.serialize.SecuritySupport$3` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$4`, `org.apache.xerces.impl.dv.SecuritySupport$4`, `org.apache.xerces.parsers.SecuritySupport$4`, `org.apache.xerces.xinclude.SecuritySupport$4`, `org.apache.xml.serialize.SecuritySupport$4` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$5`, `org.apache.xerces.impl.dv.SecuritySupport$5`, `org.apache.xerces.parsers.SecuritySupport$5`, `org.apache.xerces.xinclude.SecuritySupport$5`, `org.apache.xml.serialize.SecuritySupport$5` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$6`, `org.apache.xerces.impl.dv.SecuritySupport$6`, `org.apache.xerces.parsers.SecuritySupport$6`, `org.apache.xerces.xinclude.SecuritySupport$6`, `org.apache.xml.serialize.SecuritySupport$6` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$7`, `org.apache.xerces.impl.dv.SecuritySupport$7`, `org.apache.xerces.parsers.SecuritySupport$7`, `org.apache.xerces.xinclude.SecuritySupport$7`, `org.apache.xml.serialize.SecuritySupport$7` (same semantic_text)
- `org.apache.xerces.dom.SecuritySupport$8`, `org.apache.xerces.impl.dv.SecuritySupport$8`, `org.apache.xerces.parsers.SecuritySupport$8`, `org.apache.xerces.xinclude.SecuritySupport$8`, `org.apache.xml.serialize.SecuritySupport$8` (same semantic_text)
Identical saved embedding groups:
- `org.apache.xerces.dom.ObjectFactory`, `org.apache.xerces.impl.dv.ObjectFactory`, `org.apache.xerces.parsers.ObjectFactory`, `org.apache.xerces.xinclude.ObjectFactory`, `org.apache.xml.serialize.ObjectFactory` (same saved embedding bytes)
- `org.apache.xerces.dom.ObjectFactory$ConfigurationError`, `org.apache.xerces.impl.dv.ObjectFactory$ConfigurationError`, `org.apache.xerces.parsers.ObjectFactory$ConfigurationError`, `org.apache.xerces.xinclude.ObjectFactory$ConfigurationError`, `org.apache.xml.serialize.ObjectFactory$ConfigurationError` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport`, `org.apache.xerces.impl.dv.SecuritySupport`, `org.apache.xerces.parsers.SecuritySupport`, `org.apache.xerces.xinclude.SecuritySupport`, `org.apache.xml.serialize.SecuritySupport` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$1`, `org.apache.xerces.impl.dv.SecuritySupport$1`, `org.apache.xerces.parsers.SecuritySupport$1`, `org.apache.xerces.xinclude.SecuritySupport$1`, `org.apache.xml.serialize.SecuritySupport$1` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$2`, `org.apache.xerces.impl.dv.SecuritySupport$2`, `org.apache.xerces.parsers.SecuritySupport$2`, `org.apache.xerces.xinclude.SecuritySupport$2`, `org.apache.xml.serialize.SecuritySupport$2` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$3`, `org.apache.xerces.impl.dv.SecuritySupport$3`, `org.apache.xerces.parsers.SecuritySupport$3`, `org.apache.xerces.xinclude.SecuritySupport$3`, `org.apache.xml.serialize.SecuritySupport$3` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$4`, `org.apache.xerces.impl.dv.SecuritySupport$4`, `org.apache.xerces.parsers.SecuritySupport$4`, `org.apache.xerces.xinclude.SecuritySupport$4`, `org.apache.xml.serialize.SecuritySupport$4` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$5`, `org.apache.xerces.impl.dv.SecuritySupport$5`, `org.apache.xerces.parsers.SecuritySupport$5`, `org.apache.xerces.xinclude.SecuritySupport$5`, `org.apache.xml.serialize.SecuritySupport$5` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$6`, `org.apache.xerces.impl.dv.SecuritySupport$6`, `org.apache.xerces.parsers.SecuritySupport$6`, `org.apache.xerces.xinclude.SecuritySupport$6`, `org.apache.xml.serialize.SecuritySupport$6` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$7`, `org.apache.xerces.impl.dv.SecuritySupport$7`, `org.apache.xerces.parsers.SecuritySupport$7`, `org.apache.xerces.xinclude.SecuritySupport$7`, `org.apache.xml.serialize.SecuritySupport$7` (same saved embedding bytes)
- `org.apache.xerces.dom.SecuritySupport$8`, `org.apache.xerces.impl.dv.SecuritySupport$8`, `org.apache.xerces.parsers.SecuritySupport$8`, `org.apache.xerces.xinclude.SecuritySupport$8`, `org.apache.xml.serialize.SecuritySupport$8` (same saved embedding bytes)
These 11 duplicate-text/vector groups are expected diagnostic evidence under the frozen simple-name input contract. The input classes were not deduplicated.

## 3. Manual nearest-neighbour review

Every entry is unreviewed. Reviewer status must be one of `plausible`, `questionable`, or `unclear`; this report does not declare a neighbour correct or incorrect.

### jpetstore
#### `org.mybatis.jpetstore.domain.Order` — longest-token
kind=class; method_count=57; token_count=386; input_hash[:12]=006b4b1ce252
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `org.mybatis.jpetstore.domain.LineItem`: 0.705876001705
- `org.mybatis.jpetstore.domain.Cart`: 0.648826768960
- `org.mybatis.jpetstore.domain.Item`: 0.637909276437
- `org.mybatis.jpetstore.domain.Account`: 0.622952145264
- `org.mybatis.jpetstore.domain.CartItem`: 0.597784830237

#### `org.mybatis.jpetstore.domain.Account` — highest-method-count
kind=class; method_count=36; token_count=207; input_hash[:12]=5d95274200b9
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `org.mybatis.jpetstore.domain.Order`: 0.622952145264
- `org.mybatis.jpetstore.domain.Category`: 0.603757393043
- `org.mybatis.jpetstore.domain.Product`: 0.593167849115
- `org.mybatis.jpetstore.domain.Item`: 0.568958519111
- `org.mybatis.jpetstore.domain.LineItem`: 0.502096208612

#### `org.mybatis.jpetstore.mapper.CategoryMapper` — lowest-method-count
kind=interface; method_count=2; token_count=16; input_hash[:12]=77045e6e50f7
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public interface CategoryMapper {
    Category getCategory(String);
    List getCategoryList();
}
```
top_5_neighbors:
- `org.mybatis.jpetstore.mapper.ProductMapper`: 0.820849580660
- `org.mybatis.jpetstore.mapper.OrderMapper`: 0.737617023751
- `org.mybatis.jpetstore.mapper.LineItemMapper`: 0.688432787705
- `org.mybatis.jpetstore.mapper.AccountMapper`: 0.684283607350
- `org.mybatis.jpetstore.mapper.ItemMapper`: 0.645217810528

#### `org.mybatis.jpetstore.mapper.AccountMapper` — interface
kind=interface; method_count=8; token_count=61; input_hash[:12]=fbf942adc8a5
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `org.mybatis.jpetstore.mapper.OrderMapper`: 0.775828064549
- `org.mybatis.jpetstore.service.AccountService`: 0.740867487865
- `org.mybatis.jpetstore.mapper.CategoryMapper`: 0.684283607350
- `org.mybatis.jpetstore.mapper.LineItemMapper`: 0.655359509666
- `org.mybatis.jpetstore.mapper.ProductMapper`: 0.650388082690

#### `org.mybatis.jpetstore.web.actions.AbstractActionBean` — abstract
kind=abstract class; method_count=3; token_count=32; input_hash[:12]=32836c8944cd
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public abstract class AbstractActionBean implements ActionBean, Serializable {
    ActionBeanContext getContext();
    void setContext(ActionBeanContext);
    void setMessage(String);
}
```
top_5_neighbors:
- `org.mybatis.jpetstore.web.actions.AccountActionBean`: 0.649757736540
- `org.mybatis.jpetstore.web.actions.OrderActionBean`: 0.625636592787
- `org.mybatis.jpetstore.web.actions.CatalogActionBean`: 0.607000132855
- `org.mybatis.jpetstore.web.actions.CartActionBean`: 0.604306352989
- `org.mybatis.jpetstore.domain.Sequence`: 0.337832758024

#### `org.mybatis.jpetstore.service.AccountService` — annotated
kind=class; method_count=4; token_count=34; input_hash[:12]=425e49393467
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
@Service
public class AccountService {
    Account getAccount(String);
    Account getAccount(String, String);
    void insertAccount(Account);
    void updateAccount(Account);
}
```
top_5_neighbors:
- `org.mybatis.jpetstore.mapper.AccountMapper`: 0.740867487865
- `org.mybatis.jpetstore.service.OrderService`: 0.738912582638
- `org.mybatis.jpetstore.mapper.OrderMapper`: 0.603422379403
- `org.mybatis.jpetstore.service.CatalogService`: 0.554775264241
- `org.mybatis.jpetstore.mapper.CategoryMapper`: 0.543610927377

#### `org.mybatis.jpetstore.web.actions.AccountActionBean` — superclass
kind=class; method_count=18; token_count=107; input_hash[:12]=384028f5517a
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `org.mybatis.jpetstore.web.actions.OrderActionBean`: 0.756061062505
- `org.mybatis.jpetstore.web.actions.CatalogActionBean`: 0.749770252768
- `org.mybatis.jpetstore.web.actions.CartActionBean`: 0.718803210273
- `org.mybatis.jpetstore.web.actions.AbstractActionBean`: 0.649757736540
- `org.mybatis.jpetstore.mapper.AccountMapper`: 0.462601144310

#### `org.mybatis.jpetstore.mapper.ItemMapper` — seed-42-remainder
kind=interface; method_count=4; token_count=33; input_hash[:12]=468657031803
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public interface ItemMapper {
    int getInventoryQuantity(String);
    Item getItem(String);
    List getItemListByProduct(String);
    void updateInventoryQuantity(Map);
}
```
top_5_neighbors:
- `org.mybatis.jpetstore.mapper.ProductMapper`: 0.724543572654
- `org.mybatis.jpetstore.mapper.LineItemMapper`: 0.701373828085
- `org.mybatis.jpetstore.mapper.CategoryMapper`: 0.645217810528
- `org.mybatis.jpetstore.mapper.SequenceMapper`: 0.622024591520
- `org.mybatis.jpetstore.mapper.OrderMapper`: 0.601883927259

#### `org.mybatis.jpetstore.mapper.ProductMapper` — seed-42-remainder
kind=interface; method_count=3; token_count=26; input_hash[:12]=afd68148ad40
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public interface ProductMapper {
    Product getProduct(String);
    List getProductListByCategory(String);
    List searchProductList(String);
}
```
top_5_neighbors:
- `org.mybatis.jpetstore.mapper.CategoryMapper`: 0.820849580660
- `org.mybatis.jpetstore.mapper.ItemMapper`: 0.724543572654
- `org.mybatis.jpetstore.mapper.OrderMapper`: 0.705293966983
- `org.mybatis.jpetstore.mapper.LineItemMapper`: 0.671311464972
- `org.mybatis.jpetstore.mapper.AccountMapper`: 0.650388082690

#### `org.mybatis.jpetstore.domain.Product` — seed-42-remainder
kind=class; method_count=9; token_count=51; input_hash[:12]=e5296ac04eff
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public class Product implements Serializable {
    String getCategoryId();
    String getDescription();
    String getName();
    String getProductId();
    void setCategoryId(String);
    void setDescription(String);
    void setName(String);
    void setProductId(String);
    String toString();
}
```
top_5_neighbors:
- `org.mybatis.jpetstore.domain.Category`: 0.837673220031
- `org.mybatis.jpetstore.domain.Item`: 0.695190136093
- `org.mybatis.jpetstore.domain.CartItem`: 0.608577214368
- `org.mybatis.jpetstore.domain.Account`: 0.593167849115
- `org.mybatis.jpetstore.domain.LineItem`: 0.577464796212

### daytrader
#### `com.ibm.websphere.samples.daytrader.direct.TradeDirect` — longest-token
kind=class; method_count=65; token_count=678; input_hash[:12]=13e953a2da53
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.TradeAction`: 0.806761371160
- `com.ibm.websphere.samples.daytrader.TradeServices`: 0.803955159827
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean`: 0.677382724771
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal`: 0.577061955094
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote`: 0.560862792235

#### `com.ibm.websphere.samples.daytrader.util.TradeConfig` — highest-method-count
kind=class; method_count=70; token_count=487; input_hash[:12]=e94f37be483c
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.web.jsf.TradeConfigJSF`: 0.716872274525
- `com.ibm.websphere.samples.daytrader.TradeAction`: 0.568807016682
- `com.ibm.websphere.samples.daytrader.TradeServices`: 0.555676995235
- `com.ibm.websphere.samples.daytrader.direct.TradeDirect`: 0.549436038755
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean`: 0.476336039444

#### `com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage` — lowest-method-count
kind=interface; method_count=0; token_count=19; input_hash[:12]=e95b8733d318
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
@Qualifier
@Retention
@Target
public interface WebSocketJMSMessage extends Annotation {
}
```
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.web.websocket.MarketSummaryWebSocket`: 0.455866785082
- `com.ibm.websphere.samples.daytrader.ejb3.DTStreamer3MDB`: 0.401117902943
- `com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB`: 0.385229475268
- `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage$1`: 0.376692905455
- `com.ibm.websphere.samples.daytrader.web.websocket.JsonMessage`: 0.374763252148

#### `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage$1` — zero-method
kind=class; method_count=0; token_count=7; input_hash[:12]=57d3596e7f45
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
class ActionMessage$1 {
}
```
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.web.websocket.ActionMessage`: 0.607460004240
- `com.ibm.websphere.samples.daytrader.web.websocket.ActionDecoder`: 0.536147904828
- `com.ibm.websphere.samples.daytrader.web.jsf.TradeActionProducer`: 0.396060806460
- `com.ibm.websphere.samples.daytrader.util.WebSocketJMSMessage`: 0.376692905455
- `com.ibm.websphere.samples.daytrader.web.websocket.JsonMessage`: 0.375723744763

#### `com.ibm.websphere.samples.daytrader.TradeServices` — interface
kind=interface; method_count=22; token_count=216; input_hash[:12]=79faebc4f5a7
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.TradeAction`: 0.885107378843
- `com.ibm.websphere.samples.daytrader.direct.TradeDirect`: 0.803955159827
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean`: 0.676091661669
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote`: 0.659486186721
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal`: 0.641215885966

#### `com.ibm.websphere.samples.daytrader.ejb3.DTBroker3MDB` — annotated
kind=class; method_count=2; token_count=36; input_hash[:12]=491238598412
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
@MessageDriven
@TransactionAttribute
@TransactionManagement
public class DTBroker3MDB implements MessageListener {
    TradeServices getTrade(boolean);
    void onMessage(Message);
}
```
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.ejb3.DTStreamer3MDB`: 0.831832897838
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBBean`: 0.567830404762
- `com.ibm.websphere.samples.daytrader.direct.TradeDirect`: 0.525322918495
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBRemote`: 0.499443154696
- `com.ibm.websphere.samples.daytrader.ejb3.TradeSLSBLocal`: 0.476118075213

#### `com.ibm.websphere.samples.daytrader.util.KeyBlock` — superclass
kind=class; method_count=2; token_count=21; input_hash[:12]=64a09d222de4
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public class KeyBlock extends AbstractSequentialList {
    ListIterator listIterator(int);
    int size();
}
```
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.util.KeyBlock$KeyBlockIterator`: 0.813276016618
- `com.ibm.websphere.samples.daytrader.direct.KeySequenceDirect`: 0.543274395081
- `com.ibm.websphere.samples.daytrader.web.websocket.RecentStockChangeList`: 0.277001853425
- `com.ibm.websphere.samples.daytrader.web.websocket.JsonMessage`: 0.236697770974
- `com.ibm.websphere.samples.daytrader.entities.OrderDataBean`: 0.214853480724

#### `com.ibm.websphere.samples.daytrader.util.Log` — seed-42-remainder
kind=class; method_count=34; token_count=273; input_hash[:12]=5c88d85e0f49
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.TradeAction`: 0.396348541118
- `com.ibm.websphere.samples.daytrader.util.TimerStat`: 0.363404175935
- `com.ibm.websphere.samples.daytrader.web.TradeServletAction`: 0.361118038478
- `com.ibm.websphere.samples.daytrader.util.TradeConfig`: 0.344874977468
- `com.ibm.websphere.samples.daytrader.direct.TradeDirect`: 0.321764024804

#### `com.ibm.websphere.samples.daytrader.web.OrdersAlertFilter` — seed-42-remainder
kind=class; method_count=3; token_count=36; input_hash[:12]=92772fd1a525
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
@WebFilter
public class OrdersAlertFilter implements Filter {
    void destroy();
    void doFilter(ServletRequest, ServletResponse, FilterChain);
    void init(FilterConfig);
}
```
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.web.jsf.JSFLoginFilter`: 0.676974107687
- `com.ibm.websphere.samples.daytrader.web.TradeWebContextListener`: 0.501242002434
- `com.ibm.websphere.samples.daytrader.web.TradeAppServlet`: 0.437796564747
- `com.ibm.websphere.samples.daytrader.web.jsf.OrderDataJSF`: 0.394371831776
- `com.ibm.websphere.samples.daytrader.web.TradeServletAction`: 0.354647779463

#### `com.ibm.websphere.samples.daytrader.web.jsf.JSFLoginFilter` — seed-42-remainder
kind=class; method_count=3; token_count=37; input_hash[:12]=215ce11132c1
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
@WebFilter
public class JSFLoginFilter implements Filter {
    void destroy();
    void doFilter(ServletRequest, ServletResponse, FilterChain);
    void init(FilterConfig);
}
```
top_5_neighbors:
- `com.ibm.websphere.samples.daytrader.web.OrdersAlertFilter`: 0.676974107687
- `com.ibm.websphere.samples.daytrader.web.jsf.LoginValidator`: 0.594807826085
- `com.ibm.websphere.samples.daytrader.web.TradeWebContextListener`: 0.468593569063
- `com.ibm.websphere.samples.daytrader.web.jsf.TradeAppJSF`: 0.452097473959
- `com.ibm.websphere.samples.daytrader.web.TradeAppServlet`: 0.410197666407

### xerces
#### `org.apache.xerces.impl.xs.traversers.XSDHandler` — longest-token
kind=class; method_count=118; token_count=1501; input_hash[:12]=80fc9a7120ba
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `org.apache.xerces.impl.xs.SchemaGrammar`: 0.765894808525
- `org.apache.xerces.impl.xs.XMLSchemaValidator`: 0.720607948213
- `org.apache.xerces.impl.xs.traversers.SchemaContentHandler`: 0.704221553496
- `org.apache.xerces.impl.xs.traversers.XSDHandler$1`: 0.702994315894
- `org.apache.xerces.xinclude.XIncludeHandler`: 0.698536377769

#### `org.apache.xerces.dom.CoreDocumentImpl` — highest-method-count
kind=class; method_count=125; token_count=998; input_hash[:12]=483a6d2dce2e
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `org.apache.xerces.dom.DocumentImpl`: 0.851151648369
- `org.apache.xerces.dom.DocumentTypeImpl`: 0.752005783974
- `org.apache.xerces.impl.xs.opti.DefaultDocument`: 0.718301974423
- `org.apache.xerces.dom.DeferredDocumentImpl`: 0.715879456762
- `org.apache.xerces.dom.CoreDOMImplementationImpl`: 0.712368733412

#### `org.apache.xerces.dom.CoreDOMImplementationImpl$RevalidationHandlerHolder` — lowest-method-count
kind=class; method_count=0; token_count=12; input_hash[:12]=d4c1e4d22cf6
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
class CoreDOMImplementationImpl$RevalidationHandlerHolder {
}
```
top_5_neighbors:
- `org.apache.xerces.impl.RevalidationHandler`: 0.605952787545
- `org.apache.xerces.dom.CoreDOMImplementationImpl$XMLDTDLoaderHolder`: 0.595130342366
- `org.apache.xerces.jaxp.validation.ValidatorHandlerImpl$1`: 0.572481005096
- `org.apache.xerces.jaxp.validation.ValidatorHandlerImpl`: 0.517572252139
- `org.apache.xerces.impl.xs.traversers.XSDHandler$1`: 0.514440700409

#### `org.apache.xerces.dom.CoreDOMImplementationImpl$XMLDTDLoaderHolder` — zero-method
kind=class; method_count=0; token_count=12; input_hash[:12]=f263555e81ff
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
class CoreDOMImplementationImpl$XMLDTDLoaderHolder {
}
```
top_5_neighbors:
- `org.apache.xerces.impl.dtd.XMLDTDLoader`: 0.685682402660
- `org.apache.xerces.xni.parser.XMLDTDSource`: 0.615144222994
- `org.apache.xerces.dom.CoreDOMImplementationImpl$RevalidationHandlerHolder`: 0.595130342366
- `org.apache.xerces.xni.XMLDTDHandler`: 0.576706210861
- `org.apache.xerces.parsers.XMLGrammarPreparser$XMLGrammarLoaderContainer`: 0.571151956504

#### `org.apache.xerces.dom.DeferredNode` — interface
kind=interface; method_count=1; token_count=13; input_hash[:12]=90fbbab23e08
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public interface DeferredNode extends Node {
    int getNodeIndex();
}
```
top_5_neighbors:
- `org.apache.xerces.dom.DeferredNotationImpl`: 0.769387485453
- `org.apache.xerces.dom.DeferredElementImpl`: 0.754095810495
- `org.apache.xerces.dom.DeferredEntityImpl`: 0.720342990868
- `org.apache.xerces.dom.DeferredElementDefinitionImpl`: 0.718269122841
- `org.apache.xerces.dom.DeferredTextImpl`: 0.708463846202

#### `org.apache.xerces.dom.CharacterDataImpl` — abstract
kind=abstract class; method_count=15; token_count=122; input_hash[:12]=ff0367dfc193
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
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
top_5_neighbors:
- `org.apache.xerces.dom.TextImpl`: 0.762348055820
- `org.apache.xerces.dom.CommentImpl`: 0.732466271817
- `org.apache.xerces.dom3.as.CharacterDataEditAS`: 0.695696777781
- `org.apache.xerces.stax.events.CharactersImpl`: 0.671803813943
- `org.apache.xerces.impl.xs.opti.TextImpl`: 0.671329957060

#### `org.apache.xerces.dom.ASDOMImplementationImpl` — superclass
kind=class; method_count=4; token_count=48; input_hash[:12]=7eb08569cb6c
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public class ASDOMImplementationImpl extends DOMImplementationImpl implements DOMImplementationAS {
    ASModel createAS(boolean);
    DOMASBuilder createDOMASBuilder();
    DOMASWriter createDOMASWriter();
    DOMImplementation getDOMImplementation();
}
```
top_5_neighbors:
- `org.apache.xerces.dom3.as.DOMImplementationAS`: 0.879509150418
- `org.apache.xerces.dom.DOMImplementationImpl`: 0.723717157450
- `org.apache.xerces.parsers.DOMASBuilderImpl`: 0.718589498940
- `org.apache.xerces.dom.ASModelImpl`: 0.690694302398
- `org.apache.xerces.dom.PSVIDOMImplementationImpl`: 0.682698194442

#### `org.apache.xerces.xs.XSAttributeGroupDefinition` — seed-42-remainder
kind=interface; method_count=4; token_count=41; input_hash[:12]=3a2afd536b74
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public interface XSAttributeGroupDefinition extends XSObject {
    XSAnnotation getAnnotation();
    XSObjectList getAnnotations();
    XSObjectList getAttributeUses();
    XSWildcard getAttributeWildcard();
}
```
top_5_neighbors:
- `org.apache.xerces.impl.xs.XSAttributeGroupDecl`: 0.859296430522
- `org.apache.xerces.xs.XSModelGroupDefinition`: 0.820978458715
- `org.apache.xerces.impl.xs.XSGroupDecl`: 0.762881627906
- `org.apache.xerces.xs.XSAttributeDeclaration`: 0.740332125503
- `org.apache.xerces.xs.XSModelGroup`: 0.732372820113

#### `org.apache.xerces.xs.ElementPSVI` — seed-42-remainder
kind=interface; method_count=4; token_count=40; input_hash[:12]=bd5984641a6f
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
public interface ElementPSVI extends ItemPSVI {
    XSElementDeclaration getElementDeclaration();
    boolean getNil();
    XSNotationDeclaration getNotation();
    XSModel getSchemaInformation();
}
```
top_5_neighbors:
- `org.apache.xerces.impl.xs.ElementPSVImpl`: 0.849745243630
- `org.apache.xerces.dom.PSVIElementNSImpl`: 0.802207977503
- `org.apache.xerces.xs.ItemPSVI`: 0.782936182305
- `org.apache.xerces.xs.AttributePSVI`: 0.775370578406
- `org.apache.xerces.xs.PSVIProvider`: 0.740032673738

#### `org.apache.xerces.parsers.XMLGrammarPreparser$XMLGrammarLoaderContainer` — seed-42-remainder
kind=class; method_count=0; token_count=12; input_hash[:12]=9285916203a7
manual_review: unreviewed (`plausible` / `questionable` / `unclear`)
reviewer_note:
semantic_text:
```text
class XMLGrammarPreparser$XMLGrammarLoaderContainer {
}
```
top_5_neighbors:
- `org.apache.xerces.parsers.XMLGrammarPreparser`: 0.726595100956
- `org.apache.xerces.xni.grammars.XMLGrammarLoader`: 0.704132398466
- `org.apache.xerces.jaxp.validation.XSGrammarPoolContainer`: 0.656117900357
- `org.apache.xerces.parsers.XMLGrammarParser`: 0.642530334196
- `org.apache.xerces.impl.xs.XSLoaderImpl$XSGrammarMerger`: 0.619786534216

## 4. Re-encoding stability

| subject | classes re-encoded | exact byte matches | maximum absolute difference | minimum corresponding cosine | result |
| --- | ---: | ---: | ---: | ---: | --- |
| jpetstore | 24 | 24 | 0 | 1 | PASS |
| daytrader | 10 | 10 | 0 | 1 | PASS |
| xerces | 10 | 10 | 0 | 1 | PASS |

## 5. Current limitations

- Embeddings are generated from class declarations, not method bodies.
- Nomic was trained mainly for code retrieval; nearest-neighbour plausibility is diagnostic only, not external validation.
- Package paths are excluded, while method signatures still carry local type information.
- Runtime embeddings may not be bitwise identical across MPS, CUDA, and CPU. The saved hashes certify the frozen MPS/float16/batch-8 runtime and platform recorded in metadata.
- The formal top-3 semantic graph has not been generated.

Report generated at UTC: 2026-07-16T15:08:13Z
