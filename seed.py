from sqlmodel import Session
from database import engine, create_db_and_tables
from models import Envelope, EnvelopeType

def seed_database():
    create_db_and_tables()

    envelopes_to_add = [
    Envelope(name="Rent", category_type=EnvelopeType.EXPENSE, target=7000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Bills and Utilities", category_type=EnvelopeType.EXPENSE, target=1030.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Scooter EMI", category_type=EnvelopeType.EXPENSE, target=5403.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Medical Insurance", category_type=EnvelopeType.EXPENSE, target=800.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Hair Cut", category_type=EnvelopeType.EXPENSE, target=150.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Petrol", category_type=EnvelopeType.EXPENSE, target=1200.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Weekend Entertainment", category_type=EnvelopeType.EXPENSE, target=2000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Grocery", category_type=EnvelopeType.EXPENSE, target=500.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Personal care", category_type=EnvelopeType.EXPENSE, target=3400.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Ntorq Maintenance", category_type=EnvelopeType.EXPENSE, target=12000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Laptop Repair Fund", category_type=EnvelopeType.EXPENSE, target=15000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Health Suppliments", category_type=EnvelopeType.EXPENSE, target=750.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Cleaning Supplies", category_type=EnvelopeType.EXPENSE, target=350.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Emergency Fund", category_type=EnvelopeType.GOAL, target=100000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Meniscus Repair", category_type=EnvelopeType.GOAL, target=150000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Moving out fund", category_type=EnvelopeType.GOAL, target=70000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Teeth Repair", category_type=EnvelopeType.GOAL, target=20000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Phone", category_type=EnvelopeType.GOAL, target=50000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Duke 250 Down Payment", category_type=EnvelopeType.GOAL, target=150000.0, monthly_target=0.0, allocated=0.0),
    Envelope(name="Buffer", category_type=EnvelopeType.GOAL, target=1000.0, monthly_target=0.0, allocated=0.0),
]

    

    with Session(engine) as session:
        # Check if data already exists to avoid duplicates
        existing = session.query(Envelope).first()
        if not existing:
            session.add_all(envelopes_to_add)
            session.commit()
            print("Successfully seeded the database with your envelopes!")
        else:
            print("Database already contains data.")

if __name__ == "__main__":
    seed_database()