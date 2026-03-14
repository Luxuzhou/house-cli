import click


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
def mortgage(**kwargs):
    """Mortgage calculator for home buying."""
    pass
