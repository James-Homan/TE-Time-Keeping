import streamlit as st
import os
from utils import get_db, get_password_hash
from models import User

def run_retest_tools():
    st.sidebar.markdown("### Retest Tools")
    if st.sidebar.button("Clear all logs (admin)"):
        if clear_all_logs():
            st.sidebar.success("All logs, TS logs and user meta cleared.")
        else:
            st.sidebar.error("Failed to clear database.")
    if st.sidebar.button("Reset session state"):
        reset_session_state()
        st.sidebar.success("Session state reset.")
    if st.sidebar.button("Create test admin"):
        user = create_test_admin()
        st.sidebar.success(f"Test admin created: {user.username} (id={user.id})")
    if st.sidebar.button("Login as test admin"):
        db = get_db()
        user = db.query(User).filter(User.username == "testadmin").first()
        if not user:
            st.sidebar.error("testadmin not found — create it first.")
        else:
            st.session_state.user_id = user.id
            st.session_state.username = user.username
            st.session_state.is_admin = user.is_admin
            st.sidebar.success(f"Logged in as {user.username}")

def create_test_admin(username: str = "testadmin", password: str = "test"):
    db = get_db()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    user = User(username=username, password_hash=get_password_hash(password), is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def detect_external_user(preferred: str | None = None, allow_fallbacks: bool = False) -> bool:
    providers = [
        ("oracle", _oracle_connector, "ORACLE_USER"),
        ("agile", _agile_connector, "AGILE_USER"),
        ("baseline", _baseline_connector, "BASELINE_USER"),
    ]
    ...
    order = providers
    ...
    import getpass
    tried = []
    errors = []

    def _try_username(src_name: str, candidate: str, module=None):
        if not candidate:
            return False, f"no username from {src_name}"
        ...

    for name, module, envkey in order:
        tried.append(name)
        ...
        uname = os.environ.get(envkey)
        ...

        if not uname and module is not None and hasattr(module, "get_current_user"):
            try:
                uname = module.get_current_user()
            except Exception:
                uname = None
        ...

    if allow_fallbacks:
        os_candidates = []
        ...
        try:
            os_candidates.append(os.environ.get("USERNAME"))
        except Exception:
            pass
        ...

        for idx, cand in enumerate([c for c in os_candidates if c]):
            ok, msg = _try_username(f"os_fallback_{idx}", cand)
            if ok:
                st.success(msg)
                return True
            errors.append(msg)
        ...

    summary = "Unable to auto-detect external user. Tried: " + ", ".join(tried)
    if errors:
        summary += ". Details: " + " | ".join(errors[:5])
    st.info(summary)
    return False
