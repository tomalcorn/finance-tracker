"""Authentication module for the finance tracker application using Supabase."""

import logging

import streamlit as st
from st_supabase_connection import SupabaseConnection


def init_auth() -> SupabaseConnection:
    """Initialize authentication and return the Supabase connection.

    Returns:
        SupabaseConnection: The authenticated Supabase connection

    """
    if "supabase" not in st.session_state:
        st.session_state.supabase = st.connection("supabase", type=SupabaseConnection)

    return st.session_state.supabase


def check_authentication() -> bool:
    """Check if user is authenticated.

    Returns:
        bool: True if user is authenticated, False otherwise

    """
    conn = init_auth()

    # Check if we have a valid session
    try:
        session = conn.client.auth.get_session()
        if session and session.user:
            if "user" not in st.session_state:
                st.session_state.user = session.user
            return True
    except Exception as exc:
        # Session might be expired or invalid
        logging.exception("Authentication check failed: %s", exc)

    return False


def login_form():
    """Display login form for email/password authentication."""
    st.title("🔐 Login to Finance Tracker")

    with st.form("login_form"):
        email = st.text_input("Email", type="default")
        password = st.text_input("Password", type="password")

        col1, col2 = st.columns(2)
        with col1:
            login_button = st.form_submit_button("Login", use_container_width=True)
        with col2:
            signup_button = st.form_submit_button("Sign Up", use_container_width=True)

        if login_button:
            if email and password:
                login_user(email, password)
            else:
                st.error("Please enter both email and password")

        if signup_button:
            if email and password:
                signup_user(email, password)
            else:
                st.error("Please enter both email and password")


def login_user(email: str, password: str):
    """Authenticate user with email and password.

    Args:
        email: User's email address
        password: User's password

    """
    conn = init_auth()

    try:
        # Attempt to sign in the user
        response = conn.client.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            },
        )

        if response.user:
            st.session_state.user = response.user
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Login failed. Please check your credentials.")

    except Exception as e:
        error_message = str(e)
        if "Invalid login credentials" in error_message:
            st.error("Invalid email or password. Please try again.")
        elif "Email not confirmed" in error_message:
            st.error(
                "Please check your email and confirm your account before logging in.",
            )
        else:
            st.error(f"Login error: {error_message}")


def signup_user(email: str, password: str):
    """Register a new user with email and password.

    Args:
        email: User's email address
        password: User's password

    """
    conn = init_auth()

    try:
        # Attempt to sign up the user
        response = conn.client.auth.sign_up(
            {
                "email": email,
                "password": password,
            },
        )

        if response.user:
            if response.user.email_confirmed_at:
                st.session_state.user = response.user

                # Create user profile
                create_user_profile(response.user)

                st.success("Account created successfully! You are now logged in.")
                st.rerun()
            else:
                # Email confirmation required
                st.success(
                    "Account created! Please check your email to confirm your account before logging in.",
                )
        else:
            st.error("Signup failed. Please try again.")

    except Exception as e:
        error_message = str(e)
        if "already registered" in error_message.lower():
            st.error(
                "An account with this email already exists. Please try logging in instead.",
            )
        elif "password" in error_message.lower():
            st.error("Password must be at least 6 characters long.")
        else:
            st.error(f"Signup error: {error_message}")


def create_user_profile(user):
    """Create a user profile in the profiles table.

    Args:
        user: The Supabase user object

    """
    conn = init_auth()

    try:
        # Create profile entry
        profile_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.user_metadata.get("full_name", ""),
            "created_at": user.created_at,
        }

        conn.table("profiles").upsert(profile_data).execute()

    except Exception as e:
        # Profile creation failed, but user was created
        st.warning(f"Account created but profile setup had an issue: {e}")


def logout_user():
    """Log out the current user."""
    conn = init_auth()

    try:
        conn.client.auth.sign_out()

        # Clear session state
        if "user" in st.session_state:
            del st.session_state.user
        if "supabase" in st.session_state:
            del st.session_state.supabase

        st.success("Logged out successfully!")
        st.rerun()

    except Exception as e:
        st.error(f"Logout error: {e}")


def get_current_user():
    """Get the current authenticated user.

    Returns:
        User object if authenticated, None otherwise

    """
    if "user" in st.session_state:
        return st.session_state.user
    return None


def require_auth():
    """Decorator/function to require authentication for a page.

    Returns:
        bool: True if authenticated, False if redirected to login

    """
    if not check_authentication():
        login_form()
        return False
    return True


def show_user_info():
    """Display current user information in sidebar."""
    user = get_current_user()
    if user:
        with st.sidebar:
            st.write("---")
            st.write(f"**Logged in as:** {user.email}")
            if st.button("Logout", key="logout_button"):
                logout_user()


def reset_password_form():
    """Display password reset form."""
    st.title("🔄 Reset Password")

    with st.form("reset_password_form"):
        email = st.text_input("Enter your email address")
        submit_button = st.form_submit_button("Send Reset Email")

        if submit_button:
            if email:
                reset_password(email)
            else:
                st.error("Please enter your email address")

    if st.button("Back to Login"):
        st.rerun()


def reset_password(email: str):
    """Send password reset email.

    Args:
        email: User's email address

    """
    conn = init_auth()

    try:
        conn.client.auth.reset_password_email(email)
        st.success("Password reset email sent! Please check your inbox.")

    except Exception as e:
        st.error(f"Error sending reset email: {e}")


def auth_guard(func):
    """Decorator to protect functions that require authentication.

    Args:
        func: Function to protect

    Returns:
        Decorated function that checks authentication first

    """

    def wrapper(*args, **kwargs):
        if require_auth():
            return func(*args, **kwargs)
        return None

    return wrapper
