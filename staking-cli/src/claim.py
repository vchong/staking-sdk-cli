from web3 import Web3
from staking_sdk_py.generateCalldata import claim_rewards
from staking_sdk_py.generateTransaction import send_transaction
from staking_sdk_py.callGetters import call_getter
from staking_sdk_py.signer_factory import Signer
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.table import Table
from src.helpers import wei, amount_prompt, val_id_prompt, confirmation_prompt, count_zeros
from src.logger import init_logging

console = Console()

def claim_pending_rewards(config: dict, signer: Signer):
    # read config
    contract_address = config["contract_address"]
    rpc_url = config["rpc_url"]
    chain_id = config["chain_id"]

    validator_id = val_id_prompt(config)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    delegator_address = signer.get_address()

    table = Table(show_header=False,
        title="Claim Rewards Script Inputs",
        title_style="red bold",
        expand=True,
        show_lines=True,
    )
    table.add_column("Inputs")
    table.add_column("Values")
    table.add_row("[cyan][bold red]Validator ID[/] to claim rewards from:[/]", f"[green]{validator_id}[/]")
    table.add_row("[cyan][bold red]Funded Address:[/]", f"[green]{delegator_address}[/]")
    table.add_row("[cyan][bold red]RPC[/] to use for tx:[/]", f"[green]{rpc_url}[/]")
    table.add_row("[cyan][bold red]Staking Contract Address[/] for the network:[/]", f"[green]{contract_address}[/]")
    console.print(table)

    # PREFLIGHT CHECKS
    console.print(Panel("[bold yellow]Running Preflight Checks...[/]", title="[bold red]Preflight[/]", border_style="yellow"))

    # 1. Check if delegator has stake with this validator
    try:
        delegator_info_before = call_getter(w3, 'get_delegator', contract_address, validator_id, delegator_address)

        if not delegator_info_before or (delegator_info_before[0] == 0 and delegator_info_before[2] == 0):
            console.print("[bold red]❌ No delegation found with this validator![/]")
            console.print("[yellow]💡 You need to delegate to this validator first[/]")
            return

        active_stake = delegator_info_before[0]
        pending_stake = delegator_info_before[1]
        rewards = delegator_info_before[2]  # rewardDebt field represents claimable rewards

        console.print(f"[bold green]✅ Delegation found - Active: {active_stake}, Pending: {pending_stake}[/]")

        if rewards == 0:
            console.print("[bold yellow]⚠️  No rewards available to claim[/]")
            console.print("[yellow]💡 You may want to wait for rewards to accumulate[/]")
            return

        console.print(f"[bold green]💰 Rewards available: {rewards} wei[/]")

    except Exception as e:
        console.print(f"[bold red]❌ Error checking delegator info: {e}[/]")
        exit()

    # 2. Check validator info
    try:
        validator_info = call_getter(w3, 'get_validator', contract_address, validator_id)

        if not validator_info or validator_info[0] == "0x0000000000000000000000000000000000000000":
            console.print("[bold red]❌ Validator not found![/]")
            return
    except Exception as e:
        console.print(f"[bold red]❌ Error checking validator info: {e}[/]")
        exit()

    # 3. Get balance before claiming
    balance_before = w3.eth.get_balance(delegator_address)

    preflight_panel = Panel(
    f'''
    [cyan]Delegator delegation:[/] [green]Found ✅[/]
    [cyan]Active stake:[/] [green]{active_stake} wei[/]
    [cyan]Pending stake:[/] [green]{pending_stake} wei[/]
    [cyan]Available rewards:[/] [green]{rewards} wei[/]
    [cyan]Validator status:[/] [green]Active ✅[/]
    [cyan]Balance before:[/] [green]{balance_before} wei[/]
    ''',
        title="[bold green]Preflight Results[/]",
        border_style="green",
        padding=(1, 2)
    )
    console.print(preflight_panel)

    confirmation = confirmation_prompt("Do you want to continue claiming?", default=False)
    if not confirmation:
        return

    # Generate calldata and send transaction
    calldata_claim = claim_rewards(validator_id)
    if config["log_level"] == "debug":
        console.print(f"[cyan]Generated calldata:[/] [green]{calldata_claim}[/]")

    try:
        tx_hash = send_transaction(w3, signer, contract_address, calldata_claim, chain_id, 0)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        console.print(f"Error! while trying to send tx: {e}")
        return

    # Create formatted transaction summary
    tx_table = Table(title="Transaction Results", show_header=False, expand=True)
    tx_table.add_column("Field", style="cyan")
    tx_table.add_column("Value", style="green")
    tx_table.add_row("Status", "✅ Success" if receipt.status == 1 else "❌ Failed")
    tx_table.add_row("Transaction Hash", "0x"+receipt.transactionHash.hex())
    tx_table.add_row("Block Number", str(receipt.blockNumber))
    tx_table.add_row("Gas Used", f"{receipt.gasUsed:,}")
    tx_table.add_row("From", receipt['from'])
    tx_table.add_row("To (Contract)", receipt.to)
    console.print(tx_table)

    if receipt.status == 1:
        # Post-transaction validation
        console.print(Panel("[bold yellow]Post-Transaction Validation...[/]", title="[bold blue]Validation[/]", border_style="blue"))
        # Check delegator info after claiming
        delegator_info_after = call_getter(w3, 'get_delegator', contract_address, validator_id, delegator_address)
        console.print(f"[cyan]Delegator info after claiming:[/] [green]{delegator_info_after}[/]")
        # Check balance change
        balance_after = w3.eth.get_balance(delegator_address)
        balance_change = balance_after - balance_before
        # Calculate changes
        rewards_after = delegator_info_after[2]
        # rewards_claimed = rewards - rewards_after # Inaccurate
        validation_panel = Panel(
            f'''
            [cyan]Rewards before claiming:[/] [green]{rewards} wei[/]
            [cyan]Rewards after claiming:[/] [green]{rewards_after} wei[/]
            [cyan]Account balance change:[/] [green]{balance_change} wei[/]
            [cyan]Transaction successful![/] [green]✅[/]
            ''',
            title="[bold green]Claim Rewards Complete[/]",
            border_style="green",
            padding=(1, 2)
        )
        console.print(validation_panel)

def claim_pending_rewards_cli(config: dict, signer: Signer, val_id: int):
    log = init_logging(config["log_level"])
    # read config
    contract_address = config["contract_address"]
    rpc_url = config["rpc_url"]
    chain_id = config["chain_id"]


    w3 = Web3(Web3.HTTPProvider(rpc_url))
    delegator_address = signer.get_address()

    # 1. Check if delegator has stake with the validator
    try:
        delegator_info_before = call_getter(w3, 'get_delegator', contract_address, val_id, delegator_address)
        if not delegator_info_before or (delegator_info_before[0] == 0 and delegator_info_before[2] == 0):
            log.error("No delegation found with this validator!")
            return

        active_stake = delegator_info_before[0]
        pending_stake = delegator_info_before[1]
        rewards = delegator_info_before[2]
        log.info(f"Delegation found - Active: {active_stake}, Pending: {pending_stake}")

        if rewards == 0:
            log.error("No rewards available to claim")
            log.error("You may want to wait for rewards to accumulate[/]")
            return

        log.info(f"Rewards available: {rewards} wei")

    except Exception as e:
        log.error(f"Error checking delegator info: {e}")
        exit()

    # 2. Check validator info
    try:
        validator_info = call_getter(w3, 'get_validator', contract_address, val_id)

        if not validator_info or validator_info[0] == "0x0000000000000000000000000000000000000000":
            log.error("Validator not found!")
            return
    except Exception as e:
        log.error(f"Error checking validator info: {e}")
        exit()

    # Generate calldata and send transaction
    calldata_claim = claim_rewards(val_id)
    log.debug(f"Generated calldata: {calldata_claim}")

    # send tx
    try:
        tx_hash = send_transaction(w3, signer, contract_address, calldata_claim, chain_id, 0)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        log.error(f"Error while sending tx: {e}")
        return

    log.info(f"Tx status: {receipt.status}")
    log.info(f"Tx hash: 0x{receipt.transactionHash.hex()}")
