public class Dummy {
    public void getGrandTotal() {
        EntityQuery.from("OrderItem").queryList();
        delegator.create("OrderHeader", context);
    }
}
