"""Settings page: the preferences behind how the dashboards compute.

The composition root for the settings block, in the shape ``personal.py`` and
``joint.py`` use: every dependency is built here from ``composition.wiring`` and
passed in.

The two halves are configured separately, so the page renders one section per
half — joint only for a user who belongs to an account, since there is nothing
to configure otherwise.
"""

import streamlit as st

from composition import wiring
from domain import entities
from driving_adapters import error_boundary
from driving_adapters.blocks import settings_block

# Narrower than the dashboards' wide layout: this is a short list of controls,
# not a grid.
st.set_page_config(layout="centered")

st.title(":material/settings: Settings")
st.caption("How your personal and joint dashboards add things up.")

settings_block.flush_toast()

with error_boundary.boundary("loading your settings"):
    # Also warms the ``{user_id}:joint_accounts`` cache entry the joint-scoped
    # use case below consults to resolve its account, so it costs no extra fetch.
    joint_accounts = wiring.joint_account_repository().get_all()
    personal_use_case = wiring.manage_user_settings_use_case()
    joint_use_case = (
        wiring.manage_user_settings_use_case(entities.OwnershipType.JOINT)
        if joint_accounts
        else None
    )

personal_container = st.container(border=True)
joint_container = st.container(border=True)

with personal_container, error_boundary.boundary("loading your personal settings"):
    st.subheader(":material/dashboard: :blue[Personal]")
    settings_block.render(personal_use_case, entities.OwnershipType.PERSONAL)

with joint_container, error_boundary.boundary("loading your joint settings"):
    st.subheader(":material/group: :orange[Joint]")
    if joint_use_case is None:
        st.info(
            "You don't have a joint account yet. Once you're a member of one, "
            "its settings will appear here. See the "
            "[Joint Accounts guide](/joint_accounts) to learn how they work.",
        )
    else:
        st.caption(f":orange[Shared account] · **{joint_accounts[0].name}**")
        settings_block.render(joint_use_case, entities.OwnershipType.JOINT)
