import click
from rich.console import Console
from rich.table import Table

err_console = Console(stderr=True)


def _calc_equal_principal_interest(principal: float, monthly_rate: float, months: int):
    """等额本息: fixed monthly payment."""
    if monthly_rate == 0:
        return principal / months, principal, 0
    monthly = principal * monthly_rate * (1 + monthly_rate) ** months / (
        (1 + monthly_rate) ** months - 1
    )
    total = monthly * months
    interest = total - principal
    return monthly, total, interest


def _calc_equal_principal(principal: float, monthly_rate: float, months: int):
    """等额本金: decreasing monthly payment. Returns first month, last month, total, interest."""
    monthly_principal = principal / months
    first_month = monthly_principal + principal * monthly_rate
    last_month = monthly_principal + monthly_principal * monthly_rate
    total_interest = (principal * monthly_rate * (months + 1)) / 2
    total = principal + total_interest
    return first_month, last_month, total, total_interest


@click.command()
@click.option("--total", type=float, required=True, help="Total price (万元)")
@click.option("--down-payment", type=float, default=0.3, help="Down payment ratio (0-1)")
@click.option("--years", type=int, default=30, help="Loan term in years")
@click.option("--type", "loan_type", type=click.Choice(["commercial", "provident", "combined"]),
              default="commercial", help="Loan type")
@click.option("--method", type=click.Choice(["equal_principal_interest", "equal_principal"]),
              default="equal_principal_interest", help="Repayment method")
@click.option("--commercial-rate", type=float, default=3.45, help="Commercial loan rate (%)")
@click.option("--provident-rate", type=float, default=2.85, help="Provident fund rate (%)")
def mortgage(total, down_payment, years, loan_type, method, commercial_rate, provident_rate):
    """Mortgage calculator for home buying."""
    total_yuan = total * 10000  # 万元 -> 元
    down = total_yuan * down_payment
    loan = total_yuan - down
    months = years * 12

    table = Table(title="房贷计算", show_lines=True)
    table.add_column("项目", style="bold")
    table.add_column("数值", justify="right")

    table.add_row("房屋总价", f"{total:.2f}万元")
    table.add_row("首付比例", f"{down_payment * 100:.0f}%")
    table.add_row("首付金额", f"{down / 10000:.2f}万元")
    table.add_row("贷款金额", f"{loan / 10000:.2f}万元")
    table.add_row("贷款年限", f"{years}年")
    table.add_row("还款方式", "等额本息" if method == "equal_principal_interest" else "等额本金")

    if loan_type == "combined":
        # For combined, split evenly between commercial and provident
        half = loan / 2
        c_rate = commercial_rate / 100 / 12
        p_rate = provident_rate / 100 / 12
        if method == "equal_principal_interest":
            c_monthly, c_total, c_interest = _calc_equal_principal_interest(half, c_rate, months)
            p_monthly, p_total, p_interest = _calc_equal_principal_interest(half, p_rate, months)
            table.add_row("月供(商贷部分)", f"{c_monthly:.2f}元")
            table.add_row("月供(公积金部分)", f"{p_monthly:.2f}元")
            table.add_row("月供合计", f"{c_monthly + p_monthly:.2f}元")
            table.add_row("总利息", f"{(c_interest + p_interest) / 10000:.2f}万元")
            table.add_row("还款总额", f"{(c_total + p_total) / 10000:.2f}万元")
        else:
            c_first, c_last, c_total, c_interest = _calc_equal_principal(half, c_rate, months)
            p_first, p_last, p_total, p_interest = _calc_equal_principal(half, p_rate, months)
            table.add_row("首月月供", f"{c_first + p_first:.2f}元")
            table.add_row("末月月供", f"{c_last + p_last:.2f}元")
            table.add_row("总利息", f"{(c_interest + p_interest) / 10000:.2f}万元")
            table.add_row("还款总额", f"{(c_total + p_total) / 10000:.2f}万元")
    else:
        rate = (commercial_rate if loan_type == "commercial" else provident_rate) / 100 / 12
        rate_pct = commercial_rate if loan_type == "commercial" else provident_rate
        table.add_row("贷款利率", f"{rate_pct}%")

        if method == "equal_principal_interest":
            monthly, total_pay, interest = _calc_equal_principal_interest(loan, rate, months)
            table.add_row("月供", f"{monthly:.2f}元")
            table.add_row("总利息", f"{interest / 10000:.2f}万元")
            table.add_row("还款总额", f"{total_pay / 10000:.2f}万元")
        else:
            first, last, total_pay, interest = _calc_equal_principal(loan, rate, months)
            table.add_row("首月月供", f"{first:.2f}元")
            table.add_row("末月月供", f"{last:.2f}元")
            table.add_row("总利息", f"{interest / 10000:.2f}万元")
            table.add_row("还款总额", f"{total_pay / 10000:.2f}万元")

    err_console.print(table)
