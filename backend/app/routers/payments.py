# backend/app/routers/payments.py

import stripe
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import get_current_user
from app.database import get_supabase
from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

stripe.api_key = settings.stripe_secret_key

FRONTEND_URL = (
    "http://localhost:3000"
    if settings.environment == "development"
    else "https://www.applyafk.com"
)


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/create-checkout-session")
async def create_checkout_session(user=Depends(get_current_user)):
    """Create a Stripe Checkout Session for subscription."""

    supabase = get_supabase()

    result = supabase.table("users") \
        .select("stripe_customer_id, subscription_status, email") \
        .eq("id", user.id) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    profile = result.data

    # Don't create another session if already subscribed
    if profile.get("subscription_status") in ("active", "trialing"):
        raise HTTPException(status_code=400, detail="Already subscribed")

    # Reuse existing Stripe customer or create a new one
    customer_id = profile.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=profile.get("email", user.email),
            metadata={"supabase_user_id": user.id},
        )
        customer_id = customer.id

        # Persist immediately so we never orphan a Stripe customer
        supabase.table("users") \
            .update({"stripe_customer_id": customer_id}) \
            .eq("id", user.id) \
            .execute()

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price": settings.stripe_price_id,
            "quantity": 1,
        }],
        subscription_data={
            "metadata": {"supabase_user_id": user.id},
        },
        success_url=f"{FRONTEND_URL}/subscribe/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/subscribe",
        metadata={"supabase_user_id": user.id},
    )

    return {"checkout_url": checkout_session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    This endpoint has NO auth — Stripe calls it directly.
    Security is enforced via webhook signature verification.
    """

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info(f"Received Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        await handle_checkout_completed(data_object)
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(data_object)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(data_object)
    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(data_object)
    else:
        logger.info(f"Unhandled webhook event type: {event_type}")

    return {"status": "ok"}


@router.get("/subscription-status")
async def get_subscription_status(user=Depends(get_current_user)):
    """Check current user's subscription status."""

    supabase = get_supabase()

    result = supabase.table("users") \
        .select("subscription_status, plan, stripe_subscription_id") \
        .eq("id", user.id) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "subscription_status": result.data.get("subscription_status", "none"),
        "plan": result.data.get("plan", "free"),
        "has_subscription": result.data.get("stripe_subscription_id") is not None,
    }


@router.post("/create-portal-session")
async def create_portal_session(user=Depends(get_current_user)):
    """Create a Stripe Customer Portal session for billing management."""

    supabase = get_supabase()

    result = supabase.table("users") \
        .select("stripe_customer_id") \
        .eq("id", user.id) \
        .single() \
        .execute()

    if not result.data or not result.data.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No billing account found")

    portal_session = stripe.billing_portal.Session.create(
        customer=result.data["stripe_customer_id"],
        return_url=f"{FRONTEND_URL}/dashboard/settings",
    )

    return {"portal_url": portal_session.url}


# ============================================================
# WEBHOOK HANDLERS
# ============================================================

def _find_user_id_by_customer(supabase, customer_id: str):
    """Look up the internal user ID from a Stripe customer ID."""
    result = supabase.table("users") \
        .select("id") \
        .eq("stripe_customer_id", customer_id) \
        .single() \
        .execute()
    return result.data["id"] if result.data else None


async def handle_checkout_completed(session):
    """Called when user completes Stripe Checkout."""

    supabase = get_supabase()
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    user_id = session.get("metadata", {}).get("supabase_user_id")

    if not user_id:
        user_id = _find_user_id_by_customer(supabase, customer_id)
        if not user_id:
            logger.error(f"No user found for customer {customer_id}")
            return

    # Fetch subscription to get actual status (trialing vs active)
    subscription = stripe.Subscription.retrieve(subscription_id)

    supabase.table("users").update({
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "subscription_status": subscription.status,
        "plan": "pro",
    }).eq("id", user_id).execute()

    logger.info(f"Checkout completed for user {user_id}, status: {subscription.status}")


async def handle_subscription_updated(subscription):
    """Called when subscription status changes (trial end, renewal, etc.)."""

    supabase = get_supabase()
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    status = subscription.get("status")

    user_id = _find_user_id_by_customer(supabase, customer_id)
    if not user_id:
        logger.error(f"No user found for customer {customer_id}")
        return

    update_data = {
        "subscription_status": status,
        "stripe_subscription_id": subscription_id,
    }

    # If subscription is no longer active/trialing, deactivate automation
    if status not in ("active", "trialing"):
        update_data["is_active"] = False
        update_data["plan"] = "free"
    else:
        update_data["plan"] = "pro"

    supabase.table("users") \
        .update(update_data) \
        .eq("id", user_id) \
        .execute()

    logger.info(f"Subscription updated for user {user_id}: {status}")


async def handle_subscription_deleted(subscription):
    """Called when subscription is canceled."""

    supabase = get_supabase()
    customer_id = subscription.get("customer")

    user_id = _find_user_id_by_customer(supabase, customer_id)
    if not user_id:
        logger.error(f"No user found for customer {customer_id}")
        return

    supabase.table("users").update({
        "subscription_status": "canceled",
        "is_active": False,
        "plan": "free",
    }).eq("id", user_id).execute()

    logger.info(f"Subscription canceled for user {user_id}")


async def handle_payment_failed(invoice):
    """Called when a payment attempt fails."""

    supabase = get_supabase()
    customer_id = invoice.get("customer")

    user_id = _find_user_id_by_customer(supabase, customer_id)
    if not user_id:
        logger.error(f"No user found for customer {customer_id}")
        return

    supabase.table("users").update({
        "subscription_status": "past_due",
    }).eq("id", user_id).execute()

    logger.info(f"Payment failed for user {user_id}")
