import { useCompany } from "../company/context";
import { BALANCE_HISTORY } from "../data/balanceHistory";
import { RUB_DELTA } from "../money";
import { Amount } from "../ui/Amount";
import { Sparkline } from "../ui/charts/Sparkline";

export function AccountTile() {
  const { company } = useCompany();
  const history = BALANCE_HISTORY[company.id];
  const change = history ? history[history.length - 1] - history[0] : 0;
  return (
    <div className="card account">
      <div className="account-head">
        <span className="account-label">Расчётный счёт</span>
        <span className="account-number">{company.account}</span>
      </div>
      <div className="account-body">
        <span className="account-caption">Доступно сегодня</span>
        <Amount className="account-amount" value={company.balance} />
      </div>
      {history && (
        <div className="account-trend">
          <Sparkline values={history} label="Остаток за месяц" className="account-spark" />
          <span className="account-change">
            <strong>{RUB_DELTA.format(change)}</strong> за месяц
          </span>
        </div>
      )}
    </div>
  );
}
