exports {
    @r func total[i64] :: unit_cents:i64, quantity:i64 {
        if unit_cents < 0 or quantity < 0 { return -1; };
        return unit_cents * quantity;
    };
};
