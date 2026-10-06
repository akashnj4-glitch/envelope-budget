from sqlmodel import Session, select
from models import Envelope, Transaction, EnvelopeType
import json
from sqlmodel import select


def get_envelope_summary(session: Session, envelope_id: int) -> dict:
    envelope = session.get(Envelope, envelope_id)
    if not envelope:
        return None
    
    # 1. Fetch all transactions for this envelope
    statement = select(Transaction).where(Transaction.envelope_id == envelope_id)
    transactions = session.exec(statement).all()
    
    # 2. Calculate Total Spent
    total_spent = sum(t.amount for t in transactions)
    
    # 3. Core Zero-Based Math
    live_balance = envelope.allocated - total_spent
    deficit = max(0.0, envelope.target - live_balance)
    
    return {
        "id": envelope.id,
        "name": envelope.name,
        "type": envelope.category_type,
        "target": envelope.target,
        "monthly_target": envelope.monthly_target,
        "allocated": envelope.allocated,
        "spent": total_spent,
        "live_balance": live_balance,
        "deficit": deficit
    }

def get_all_summaries(session: Session) -> list[dict]:
    envelopes = session.exec(select(Envelope)).all()
    summaries = [get_envelope_summary(session, env.id) for env in envelopes]
    
    # 1. Calculate total overspending (all negative balances in EXPENSE envelopes)
    total_overspend = 0.0
    for env in summaries:
        if env["type"] == EnvelopeType.EXPENSE and env["live_balance"] < 0:
            # If balance is -100, we add 100 to the total overspend tally
            total_overspend += abs(env["live_balance"])
            
    # 2. Find the Buffer envelope and subtract the total overspend from its balance
    for env in summaries:
        if env["name"] == "Buffer":
            env["live_balance"] -= total_overspend
            break
            
    return summaries

def log_transaction(session: Session, envelope_id: int, amount: float, note: str = ""):
    new_transaction = Transaction(envelope_id=envelope_id, amount=amount, note=note)
    session.add(new_transaction)
    session.commit()
    session.refresh(new_transaction)
    return new_transaction

from sqlmodel import desc

def get_all_transactions(session: Session) -> list[Transaction]:
    # Fetch all transactions ordered by newest first
    statement = select(Transaction).order_by(desc(Transaction.timestamp))
    return session.exec(statement).all()

def get_transaction(session: Session, transaction_id: int):
    return session.get(Transaction, transaction_id)

def update_transaction(session: Session, transaction_id: int, amount: float, envelope_id: int, note: str):
    transaction = session.get(Transaction, transaction_id)
    if transaction:
        transaction.amount = amount
        transaction.envelope_id = envelope_id
        transaction.note = note
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
    return transaction

def delete_transaction(session: Session, transaction_id: int):
    transaction = session.get(Transaction, transaction_id)
    if transaction:
        # If it's an allocation, reverse the math on all envelopes first
        if transaction.is_allocation:
            allocations = json.loads(transaction.allocation_data)
            for str_env_id, amount in allocations.items():
                envelope = session.get(Envelope, int(str_env_id))
                if envelope:
                    envelope.allocated -= amount
                    session.add(envelope)
        
        # Then delete the transaction log
        session.delete(transaction)
        session.commit()

def allocate_funds(session: Session, allocations: dict[int, float]):
    total_allocated = sum(allocations.values())
    if total_allocated <= 0:
        return

    # 1. Add the money to the envelopes
    for env_id, amount in allocations.items():
        if amount > 0:
            envelope = session.get(Envelope, env_id)
            if envelope:
                envelope.allocated += amount
                session.add(envelope)
    
    # 2. Log the single master transaction
    allocation_txn = Transaction(
        amount=total_allocated,
        envelope_id=None,
        note="Income Allocation",
        is_allocation=True,
        allocation_data=json.dumps(allocations) # Hides the breakdown here
    )
    session.add(allocation_txn)
    session.commit()

def create_envelope(session: Session, name: str, category_type: EnvelopeType, target: float, monthly_target: float):
    # 1. Check if an envelope with this name already exists
    statement = select(Envelope).where(Envelope.name == name)
    existing = session.exec(statement).first()
    
    if existing:
        return False
        
    # 2. If it is unique, proceed with creating it, including the monthly target
    new_env = Envelope(
        name=name, 
        category_type=category_type, 
        target=target, 
        monthly_target=monthly_target, 
        allocated=0.0
    )
    session.add(new_env)
    session.commit()
    session.refresh(new_env)
    return new_env

def update_envelope(session: Session, envelope_id: int, name: str, target: float, monthly_target: float):
    envelope = session.get(Envelope, envelope_id)
    if not envelope:
        return False, "Envelope not found."
    
    # If you are changing the name, check if the new name is already taken
    if envelope.name != name:
        statement = select(Envelope).where(Envelope.name == name)
        existing = session.exec(statement).first()
        if existing:
            return False, f"An envelope named '{name}' already exists."
    
    # Apply the updates
    envelope.name = name
    envelope.target = target
    envelope.monthly_target = monthly_target
    
    session.add(envelope)
    session.commit()
    session.refresh(envelope)
    
    return True, envelope

def delete_envelope(session: Session, envelope_id: int):
    envelope = session.get(Envelope, envelope_id)
    if envelope:
        # Delete associated transactions first to prevent foreign key errors
        for txn in envelope.transactions:
            session.delete(txn)
            
        # Delete the envelope itself
        session.delete(envelope)
        session.commit()