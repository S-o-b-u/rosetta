package org.apache.ofbiz.order.rosetta;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.ofbiz.entity.Delegator;
import org.apache.ofbiz.entity.DelegatorFactory;
import org.apache.ofbiz.entity.GenericValue;
import org.apache.ofbiz.order.shoppingcart.ShoppingCart;

import java.math.BigDecimal;
import java.util.Locale;

/**
 * Independent stdin/stdout oracle for Rosetta's getGrandTotal parity checks.
 * The adapter must run with an initialized OFBiz delegator and component classpath.
 */
public final class RosettaBaselineAdapter {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private RosettaBaselineAdapter() {
    }

    public static void main(String[] args) throws Exception {
        JsonNode fixture = MAPPER.readTree(System.in);
        Delegator delegator = DelegatorFactory.getDelegator("default");
        if (delegator == null) {
            throw new IllegalStateException("Unable to load the OFBiz default delegator.");
        }

        ShoppingCart cart = new ShoppingCart(delegator, null, Locale.US, "USD");
        addCartItems(cart, fixture.path("cart_lines"));
        addShippingAndTax(cart, fixture.path("ship_info"));
        addAdjustments(cart, fixture.path("adjustments"));
        addAdjustments(cart, fixture.path("global_adjustments"));

        ObjectNode result = MAPPER.createObjectNode();
        result.put("sub_total", cart.getSubTotal().toPlainString());
        result.put("total_shipping", cart.getTotalShipping().toPlainString());
        result.put("total_sales_tax", cart.getTotalSalesTax().toPlainString());
        result.put("order_other_adjustment_total", cart.getOrderOtherAdjustmentTotal().toPlainString());
        result.put("order_global_adjustments", cart.getOrderGlobalAdjustments().toPlainString());
        result.put("grand_total", cart.getGrandTotal().toPlainString());
        System.out.println(MAPPER.writeValueAsString(result));
    }

    private static void addCartItems(ShoppingCart cart, JsonNode lines) throws Exception {
        for (JsonNode line : lines) {
            BigDecimal subtotal = decimal(line, "item_sub_total", BigDecimal.ZERO);
            BigDecimal quantity = decimal(line, "quantity", BigDecimal.ONE);
            BigDecimal unitPrice = subtotal.divide(quantity, 10, java.math.RoundingMode.HALF_UP);
            cart.addNonProductItem(
                    "ITEM",
                    line.path("item_name").asText("Rosetta test item"),
                    null,
                    unitPrice,
                    quantity,
                    null,
                    null,
                    null,
                    cart.getDispatcher());
        }
    }

    private static void addShippingAndTax(ShoppingCart cart, JsonNode shipInfo) {
        for (JsonNode ship : shipInfo) {
            int group = cart.addShipInfo();
            cart.setItemShipGroupEstimate(decimal(ship, "ship_estimate", BigDecimal.ZERO), group);
            BigDecimal tax = decimal(ship, "total_tax", BigDecimal.ZERO);
            if (tax.signum() != 0) {
                GenericValue taxAdjustment = cart.getDelegator().makeValue("OrderAdjustment");
                taxAdjustment.set("orderAdjustmentTypeId", "SALES_TAX");
                taxAdjustment.set("amount", tax);
                taxAdjustment.set("taxAuthGeoId", "ROSETTA");
                taxAdjustment.set("taxAuthPartyId", "ROSETTA");
                cart.getShipInfo(group).addShipTaxAdj(taxAdjustment);
            }
        }
    }

    private static void addAdjustments(ShoppingCart cart, JsonNode adjustments) {
        for (JsonNode adjustment : adjustments) {
            GenericValue value = cart.getDelegator().makeValue("OrderAdjustment");
            value.set("orderAdjustmentTypeId", "OTHER_CHARGE");
            value.set("amount", decimal(adjustment, "amount", BigDecimal.ZERO));
            if (adjustment.path("is_percent").asBoolean(false)) {
                value.set("amount", null);
                value.set("sourcePercentage", decimal(adjustment, "amount", BigDecimal.ZERO));
            }
            String shipGroup = adjustment.path("ship_group_seq_id").isNull()
                    ? null : adjustment.path("ship_group_seq_id").asText(null);
            value.set("shipGroupSeqId", shipGroup);
            cart.addAdjustment(value);
        }
    }

    private static BigDecimal decimal(JsonNode node, String field, BigDecimal fallback) {
        JsonNode value = node.get(field);
        if (value == null || value.isNull() || value.asText().isBlank()) {
            return fallback;
        }
        return new BigDecimal(value.asText());
    }
}
