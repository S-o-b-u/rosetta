# Legacy Baseline Adapter Contract

Rosetta's `java_executed` equivalence mode runs an external legacy adapter for each canonical test case. The adapter can be a small Java harness that loads the legacy application or an OFBiz test endpoint.

## Protocol

The adapter receives exactly one JSON object on standard input and must write exactly one JSON object to standard output.

Example input:

```json
{
  "cart_lines": [{"item_sub_total": "120.00"}],
  "ship_info": [{"ship_estimate": "10.00", "total_tax": "8.40"}],
  "adjustments": [{"amount": "-10.00"}],
  "global_adjustments": [{"amount": "2.00", "ship_group_seq_id": null}]
}
```

Example output:

```json
{
  "sub_total": "120.00",
  "total_shipping": "10.00",
  "total_sales_tax": "8.40",
  "order_other_adjustment_total": "-10.00",
  "order_global_adjustments": "2.00",
  "grand_total": "130.40"
}
```

The adapter must execute the actual legacy method and must not call the modern service or Gemini to produce its answer. Diagnostics belong on standard error; standard output is reserved for the response JSON.

## Running It

Pass the adapter command to the migration CLI:

```text
python rosetta-cli/rosetta.py migrate --file <legacy-file> --target <method> --baseline-mode java_executed --baseline-command "<adapter command>"
```

Rosetta fails closed when the command is missing, exits unsuccessfully, returns invalid JSON, or returns a non-object response.

## OFBiz Adapter

The first OFBiz implementation is [RosettaBaselineAdapter.java](../../ofbiz-framework/applications/order/src/test/java/org/apache/ofbiz/order/rosetta/RosettaBaselineAdapter.java). It creates a real `ShoppingCart`, adds non-product cart items, attaches shipping and `SALES_TAX` adjustments to ship groups, adds order adjustments, and calls the public OFBiz total methods.

It must run with an initialized OFBiz delegator because tax and adjustment calculations depend on OFBiz entity metadata. Compile it after installing a JDK and setting `JAVA_HOME`:

```cmd
cd /d C:\path\to\rosetta\ofbiz-framework
gradlew.bat :applications:order:compileTestJava
```

The exact runtime classpath is environment-specific. Launch `org.apache.ofbiz.order.rosetta.RosettaBaselineAdapter` with the order test classes and an initialized `default` delegator, then verify the protocol independently:

```cmd
type getGrandTotal_case.json | java -cp "<ofbiz-runtime-classpath>" org.apache.ofbiz.order.rosetta.RosettaBaselineAdapter
```