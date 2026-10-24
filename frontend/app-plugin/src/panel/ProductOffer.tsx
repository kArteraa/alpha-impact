import { useId } from "react";
import type { ProductOffer as Offer } from "../types";

export function ProductOffer({ offer }: { offer: Offer }) {
  const headingId = useId();
  return (
    <section className="product-offer" aria-labelledby={headingId}>
      <h4 id={headingId}>Продукт банка</h4>
      <p>
        <strong>{offer.product}</strong>
      </p>
      <p className="product-reason">{offer.reason}</p>
      <button type="button" className="button-secondary">
        Узнать подробнее
      </button>
    </section>
  );
}
