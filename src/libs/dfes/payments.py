"""Module for the payments DataFrame Editor."""

import pydantic
import streamlit as st

from libs import models
from libs.buttons import add


class AddPaymentButton(add.AddButton):
    """Class representing an 'Add Payment' button in the UI."""

    def _submit_new_row(self, new_row: dict) -> None:
        """Handle the submission of a new payment row."""
        # Validate
        try:
            new_payment = models.PaymentsModel(**new_row)
            # If validation passes, proceed with adding the payment
        except pydantic.ValidationError as e:
            st.error(f"Error adding payment: {e}")
