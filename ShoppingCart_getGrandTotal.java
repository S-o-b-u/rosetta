public BigDecimal getGrandTotal() {
        // sales tax and shipping are not stored as adjustments but rather as part of the ship group
        return this.getSubTotal().add(this.getTotalShipping()).add(this.getTotalSalesTax()).add(this.getOrderOtherAdjustmentTotal())
                .add(this.getOrderGlobalAdjustments());
    }
