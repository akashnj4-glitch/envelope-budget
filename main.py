from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from database import create_db_and_tables, get_session
from models import Envelope, Transaction, EnvelopeType
import services
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List

# This runs once when the server starts to create budget.db
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/api/envelopes")
def read_all_envelopes(session: Session = Depends(get_session)):
    return services.get_all_summaries(session)

@app.get("/api/envelopes/{envelope_id}")
def read_envelope(envelope_id: int, session: Session = Depends(get_session)):
    summary = services.get_envelope_summary(session, envelope_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Envelope not found")
    return summary

@app.post("/api/transactions")
def create_transaction(envelope_id: int, amount: float, note: str = "", session: Session = Depends(get_session)):
    # Log the expense
    services.log_transaction(session, envelope_id, amount, note)
    
    # Return the updated math for that envelope immediately
    return services.get_envelope_summary(session, envelope_id)


# Set up the HTML templates directory
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def mobile_dashboard(request: Request, session: Session = Depends(get_session)):
    envelopes_data = services.get_all_summaries(session)
    transactions_data = services.get_all_transactions(session)
    
    # Extract the Buffer envelope so we can display it specifically
    buffer_data = next((env for env in envelopes_data if env["name"] == "Buffer"), None)
    
    return templates.TemplateResponse(
        request=request, name="dashboard.html", 
        context={
            "envelopes": envelopes_data, 
            "transactions": transactions_data,
            "buffer": buffer_data
        }
    )

@app.post("/api/transactions/web")
def log_transaction_web(
    envelope_id: int = Form(...), 
    amount: float = Form(...), 
    session: Session = Depends(get_session)
):
    services.log_transaction(session, envelope_id, amount, note="Mobile Entry")
    return RedirectResponse(url="/", status_code=303)


@app.get("/expense/new", response_class=HTMLResponse)
def new_expense_form(request: Request, session: Session = Depends(get_session)):
    envelopes_data = services.get_all_summaries(session)
    return templates.TemplateResponse(
        request=request, name="expense_form.html", context={"envelopes": envelopes_data}
    )

@app.post("/transaction/{transaction_id}/delete")
def delete_transaction_web(transaction_id: int, session: Session = Depends(get_session)):
    services.delete_transaction(session, transaction_id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/transaction/{transaction_id}/edit", response_class=HTMLResponse)
def edit_transaction_form(transaction_id: int, request: Request, session: Session = Depends(get_session)):
    transaction = services.get_transaction(session, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    envelopes_data = services.get_all_summaries(session)
    return templates.TemplateResponse(
        request=request, name="edit_expense_form.html", 
        context={"transaction": transaction, "envelopes": envelopes_data}
    )

@app.post("/transaction/{transaction_id}/edit")
def edit_transaction_submit(
    transaction_id: int,
    envelope_id: int = Form(...),
    amount: float = Form(...),
    note: str = Form(""),
    session: Session = Depends(get_session)
):
    services.update_transaction(session, transaction_id, amount, envelope_id, note)
    return RedirectResponse(url="/", status_code=303)

@app.get("/income/new", response_class=HTMLResponse)
def new_income_form(request: Request, session: Session = Depends(get_session)):
    envelopes_data = services.get_all_summaries(session)
    return templates.TemplateResponse(
        request=request, name="income_allocation.html", context={"envelopes": envelopes_data}
    )

@app.post("/income/allocate")
async def process_allocation(request: Request, session: Session = Depends(get_session)):
    # Read the dynamic form inputs
    form_data = await request.form()
    allocations = {}
    
    # Loop through the form fields to find the envelope inputs
    for key, value in form_data.items():
        if key.startswith("alloc_") and value.strip():
            try:
                env_id = int(key.split("_")[1])
                amount = float(value)
                if amount > 0:
                    allocations[env_id] = amount
            except ValueError:
                pass
                
    # Send the math to the logic layer
    services.allocate_funds(session, allocations)
    return RedirectResponse(url="/", status_code=303)

@app.get("/envelope/new", response_class=HTMLResponse)
def new_envelope_form(request: Request, type: str = "Expense"):
    return templates.TemplateResponse(
        request=request, name="envelope_form.html", context={"default_type": type}
    )

@app.post("/envelope/new")
def create_envelope_submit(
    request: Request,
    name: str = Form(...),
    category_type: str = Form(...),
    target: float = Form(0.0),
    monthly_target: float = Form(0.0),  # Receive the new input
    session: Session = Depends(get_session)
):
    env_type = EnvelopeType.EXPENSE if category_type == "Expense" else EnvelopeType.GOAL
    
    # Pass monthly_target to the service
    success = services.create_envelope(session, name, env_type, target, monthly_target)
    if not success:
        return templates.TemplateResponse(
            request=request, 
            name="envelope_form.html", 
            context={
                "default_type": category_type, 
                "error": f"An envelope named '{name}' already exists."
            }
        )
        
    return RedirectResponse(url="/", status_code=303)

@app.get("/envelope/{envelope_id}", response_class=HTMLResponse)
def view_envelope(request: Request, envelope_id: int, session: Session = Depends(get_session)):
    # Reusing your existing summary logic so we have all the calculated fields if needed
    summary = services.get_envelope_summary(session, envelope_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Envelope not found")
        
    return templates.TemplateResponse(
        request=request, 
        name="envelope_detail.html", 
        context={"env": summary}
    )

@app.post("/envelope/{envelope_id}/edit")
def edit_envelope_submit(
    request: Request,
    envelope_id: int,
    name: str = Form(...),
    target: float = Form(0.0),
    monthly_target: float = Form(0.0),
    session: Session = Depends(get_session)
):
    success, result = services.update_envelope(session, envelope_id, name, target, monthly_target)
    
    if not success:
        # If the duplicate name check failed, reload the page with the red error box
        summary = services.get_envelope_summary(session, envelope_id)
        return templates.TemplateResponse(
            request=request, 
            name="envelope_detail.html", 
            context={"env": summary, "error": result}
        )
        
    return RedirectResponse(url="/", status_code=303)

@app.post("/envelope/{envelope_id}/delete")
def delete_envelope_submit(
    envelope_id: int,
    session: Session = Depends(get_session)
):
    services.delete_envelope(session, envelope_id)
    return RedirectResponse(url="/", status_code=303)

# reordering the envelop list.

class ReorderRequest(BaseModel):
    envelope_ids: List[int]

@app.put("/api/envelopes/reorder")
def reorder_envelopes(request: ReorderRequest, session: Session = Depends(get_session)):
    # Loop through the submitted IDs and update their position to match their new index
    for index, env_id in enumerate(request.envelope_ids):
        envelope = session.get(Envelope, env_id)
        if envelope:
            envelope.position = index
    
    session.commit()
    return {"status": "success"}