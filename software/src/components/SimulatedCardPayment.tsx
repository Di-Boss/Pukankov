import { useEffect, useState } from "react";
import { CreditCard, ShieldCheck, CheckCircle2 } from "lucide-react";

export function SimulatedCardPayment({
  transactionSuccess,
  onTransactionSuccess,
  onValidChange,
}: {
  transactionSuccess: boolean;
  onTransactionSuccess: (value: boolean) => void;
  onValidChange: (value: boolean) => void;
}) {
  const [number, setNumber] = useState(""),
    [holder, setHolder] = useState(""),
    [expiry, setExpiry] = useState(""),
    [cvv, setCvv] = useState("");
  const digits = number.replace(/\D/g, "");
  const match = /^(0[1-9]|1[0-2])\/(\d{2})$/.exec(expiry);
  const now = new Date();
  const validExpiry =
    !!match &&
    (2000 + Number(match[2]) > now.getFullYear() ||
      (2000 + Number(match[2]) === now.getFullYear() &&
        Number(match[1]) >= now.getMonth() + 1));
  const valid =
    digits.length === 16 &&
    holder.trim().length >= 3 &&
    validExpiry &&
    /^\d{3,4}$/.test(cvv);
  useEffect(() => onValidChange(valid), [valid, onValidChange]);
  return (
    <div className="card-payment">
      <div className="section-heading">
        <h2>
          <CreditCard size={19} />
          Плащане с карта
        </h2>
        <span className="simulation-badge">УЧЕБЕН СИМУЛАТОР</span>
      </div>
      <div className="payment-card-preview" aria-hidden="true">
        <div>
          <span>PUKANKOV</span>
          <CreditCard size={25} />
        </div>
        <div className="card-chip" />
        <strong>{number || "•••• •••• •••• ••••"}</strong>
        <div>
          <span>{holder.toUpperCase() || "ИМЕ НА ПРИТЕЖАТЕЛЯ"}</span>
          <span>{expiry || "MM / YY"}</span>
        </div>
      </div>
      <div className="card-fields">
        <label className="card-field-full">
          Номер на карта
          <input
            aria-label="Номер на карта"
            autoComplete="off"
            inputMode="numeric"
            value={number}
            maxLength={19}
            placeholder="4242 4242 4242 4242"
            onChange={(e) =>
              setNumber(
                e.target.value
                  .replace(/\D/g, "")
                  .slice(0, 16)
                  .replace(/(.{4})/g, "$1 ")
                  .trim(),
              )
            }
          />
        </label>
        <label className="card-field-full">
          Име на притежателя
          <input
            aria-label="Име на притежателя"
            autoComplete="off"
            value={holder}
            maxLength={80}
            placeholder="IVAN IVANOV"
            onChange={(e) => setHolder(e.target.value)}
          />
        </label>
        <label>
          Валидна до
          <input
            aria-label="Валидна до"
            autoComplete="off"
            inputMode="numeric"
            value={expiry}
            maxLength={5}
            placeholder="MM/YY"
            onChange={(e) => {
              const n = e.target.value.replace(/\D/g, "").slice(0, 4);
              setExpiry(n.length > 2 ? n.slice(0, 2) + "/" + n.slice(2) : n);
            }}
          />
        </label>
        <label>
          CVV
          <input
            aria-label="CVV"
            autoComplete="off"
            inputMode="numeric"
            type="password"
            value={cvv}
            maxLength={4}
            placeholder="123"
            onChange={(e) =>
              setCvv(e.target.value.replace(/\D/g, "").slice(0, 4))
            }
          />
        </label>
      </div>
      <div className="card-test-info">
        <ShieldCheck size={16} />
        <p>
          Използвай само измислени данни. Картата не се изпраща до сървъра и не
          се съхранява. Не се прехвърлят реални средства.
        </p>
      </div>
      <button
        type="button"
        className="text-link fill-test-card"
        onClick={() => {
          setNumber("4242 4242 4242 4242");
          setHolder("IVAN IVANOV");
          setExpiry("12/" + String(now.getFullYear() + 3).slice(-2));
          setCvv("123");
        }}
      >
        Попълни примерна карта
      </button>
      <label
        className={`transaction-toggle ${transactionSuccess ? "approved" : ""}`}
      >
        <input
          type="checkbox"
          checked={transactionSuccess}
          onChange={(e) => onTransactionSuccess(e.target.checked)}
          aria-label="Успешна транзакция"
        />
        <span>
          <strong>Успешна транзакция</strong>
          <small>
            {transactionSuccess
              ? "Симулаторът ще одобри плащането."
              : "Без отметка симулаторът ще откаже плащането."}
          </small>
        </span>
        <CheckCircle2 size={20} />
      </label>
    </div>
  );
}
