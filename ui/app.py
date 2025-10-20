import os
import httpx
import streamlit as st
import time


API_URL = os.getenv("API_URL", "http://localhost:8000")


def login(username: str, password: str):
    with httpx.Client(timeout=10) as client:
        resp = client.post(f"{API_URL}/auth/login", json={"username": username, "password": password})
        resp.raise_for_status()
        return resp.json()


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def me():
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{API_URL}/auth/me", headers=auth_headers())
        resp.raise_for_status()
        return resp.json()


def list_tickets(page=1, size=10, search=None, status=None, worker_id=None):
    params = {"page": page, "size": size}
    if search:
        params["search"] = search
    if status:
        params["status"] = status
    if worker_id:
        params["worker_id"] = worker_id
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{API_URL}/tickets/", params=params, headers=auth_headers())
        resp.raise_for_status()
        return resp.json()


def update_ticket_status(ticket_id: int, new_status: str):
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{API_URL}/tickets/{ticket_id}/status",
            params={"new_status": new_status},
            headers=auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()


def set_ticket_viewed(ticket_id: int, viewed: bool):
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{API_URL}/tickets/{ticket_id}/viewed",
            json={"viewed": viewed},
            headers=auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()


def assign_ticket(ticket_id: int, worker_id: int):
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{API_URL}/tickets/{ticket_id}/assign",
            params={"worker_id": worker_id},
            headers=auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()


def list_users():
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{API_URL}/users/", headers=auth_headers())
        resp.raise_for_status()
        return resp.json()


def tickets_stats(worker_id: int):
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{API_URL}/tickets/stats", params={"worker_id": worker_id}, headers=auth_headers())
        resp.raise_for_status()
        return resp.json()


def create_user(username: str, password: str, role: str):
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{API_URL}/users/",
            json={"username": username, "password": password, "role": role},
            headers=auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()


def delete_user(user_id: int):
    with httpx.Client(timeout=10) as client:
        resp = client.delete(f"{API_URL}/users/{user_id}", headers=auth_headers())
        if resp.status_code not in (200, 204):
            resp.raise_for_status()
        return True


def create_public_ticket(title: str, description: str, client_name: str, client_email: str):
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{API_URL}/public/tickets",
            json={
                "title": title,
                "description": description,
                "client": {"name": client_name, "email": client_email},
            },
        )
        resp.raise_for_status()
        return resp.json()


def main():
    st.set_page_config(page_title="Repair Requests", layout="wide")

    # Special standalone view for worker tasks (opens in new tab via link)
    try:
        params = st.query_params
    except Exception:
        params = {}
    mode = params.get("mode")
    if mode == "worker_tasks":
        # Require auth
        if not st.session_state.get("token"):
            # exchange short-lived view token (vt) to session token
            vt = params.get("vt")
            if vt:
                try:
                    # trust vt directly as bearer for view context
                    st.session_state["token"] = vt
                    st.session_state["user"] = {"role": "admin", "username": "view"}
                except Exception:
                    pass
        if not st.session_state.get("token"):
            st.error("Login required")
            return

        worker_id = params.get("worker_id")
        if not worker_id:
            st.error("Worker is not specified")
            return
        st.title("Worker Tasks")
        status_tab = st.tabs(["New", "In Progress", "Done"])  # viewed is visual state, use status
        page = int(params.get("page") or 1)
        size = int(params.get("size") or 10)

        def render_list(_status: str):
            try:
                data = list_tickets(page=page, size=size, status=_status, worker_id=int(worker_id))
            except Exception as e:
                st.error(str(e))
                return
            for item in data.get("items", []):
                with st.expander(f"#{item['id']} {item['title']}"):
                    st.write(item["description"])
            st.write(f"Total: {data.get('total')}")

        with status_tab[0]:
            render_list("new")
        with status_tab[1]:
            render_list("in_progress")
        with status_tab[2]:
            render_list("done")
        return

    # Top bar with login/logout on the right
    left, right = st.columns([5, 1])
    with left:
        st.title("Repair Requests")

    if "token" not in st.session_state:
        st.session_state["token"] = None
    if "user" not in st.session_state:
        st.session_state["user"] = None
    if "show_login_dialog" not in st.session_state:
        st.session_state["show_login_dialog"] = False
    if "show_create_worker_dialog" not in st.session_state:
        st.session_state["show_create_worker_dialog"] = False

    # Restore token from URL query params if present and not expired
    try:
        params = st.query_params
        q_token = params.get("token")
        q_exp = params.get("exp")
        if not st.session_state.get("token") and q_token and q_exp:
            try:
                if int(q_exp) > int(time.time()):
                    st.session_state["token"] = q_token
                    # load user silently
                    try:
                        st.session_state["user"] = me()
                    except Exception:
                        pass
                else:
                    # expired -> clear params
                    st.query_params.clear()
            except Exception:
                pass
    except Exception:
        pass

    def do_logout():
        st.session_state["token"] = None
        st.session_state["user"] = None
        try:
            st.query_params.clear()
        except Exception:
            pass

    with right:
        if st.session_state.get("token") and st.session_state.get("user"):
            st.write("")
            if st.button("Logout"):
                do_logout()
                st.rerun()
        else:
            if st.button("Login"):
                st.session_state["show_login_dialog"] = True

    if st.session_state.get("show_login_dialog") and (not st.session_state.get("token")):
        @st.dialog("Login")
        def login_dialog():
            username = st.text_input("Username", key="dlg_login_user")
            password = st.text_input("Password", type="password", key="dlg_login_pass")
            col_a, col_b = st.columns([1, 1])
            with col_a:
                if st.button("Cancel", key="dlg_login_cancel"):
                    st.session_state["show_login_dialog"] = False
                    st.rerun()
            with col_b:
                if st.button("Sign in", key="dlg_login_btn"):
                    try:
                        data = login(username, password)
                        token = data.get("access_token")
                        st.session_state["token"] = token
                        st.session_state["user"] = me()
                        # persist token for 1 hour in URL params
                        exp = int(time.time()) + 3600
                        try:
                            st.query_params.update({"token": token, "exp": str(exp)})
                        except Exception:
                            pass
                        st.session_state["show_login_dialog"] = False
                        st.success("Logged in")
                        st.rerun()
                    except Exception as e:
                        if "400" in str(e) or "Bad Request" in str(e):
                            st.error("Incorrect username or password. Please check your credentials.")
                        else:
                            st.error(str(e))
        login_dialog()

    # If logged in, hide Public Form; otherwise show only Public Form
    if not st.session_state.get("token"):
        st.subheader("Submit a Repair Request")
        with st.form("public_form", clear_on_submit=False):
            title = st.text_input("Title")
            description = st.text_area("Description")
            client_name = st.text_input("Your Name")
            client_email = st.text_input("Your Email")
            submitted = st.form_submit_button("Submit")
            
            # Validate before submission
            if submitted:
                if not title or not description or not client_name or not client_email:
                    st.error("Please fill in all required fields")
                elif "@" not in client_email or "." not in client_email.split("@")[-1]:
                    st.error("Please enter a valid email address")
                else:
                    try:
                        data = create_public_ticket(title, description, client_name, client_email)
                        st.success(f"Created ticket #{data.get('id')}")
                        st.rerun()  # Clear form after successful submission
                    except Exception as e:
                        if "409" in str(e) or "Conflict" in str(e):
                            st.error("A ticket with the same title, description, and email already exists. Please modify your request.")
                        else:
                            st.error(str(e))
        return

    # App features only when logged in
    tab_app = st.container()

    with tab_app:
        if not st.session_state.get("user"):
            try:
                st.session_state["user"] = me()
            except Exception as e:
                st.error(str(e))
                return

        user = st.session_state["user"]
        role = user.get("role")

        tabs = st.tabs(["Tickets", "Workers"]) if role == "admin" else [st.container()]
        tab_tickets = tabs[0]
        tab_workers = tabs[1] if role == "admin" and len(tabs) > 1 else None

        with tab_tickets:
            # Fetch once for categorization; per-tab pagination below
            default_page_size = 10
            try:
                data = list_tickets(page=1, size=100, search=None, status=None)
            except Exception as e:
                st.error(str(e))
                return

            # Categorize for admin view
            if role == "admin":
                cat_tabs = st.tabs(["New", "Assigned", "In Progress", "Done"]) 
                items = data.get("items", [])
                new_items = [i for i in items if i.get("status") == "new" and not i.get("worker")]
                assigned_items = [i for i in items if (i.get("worker") is not None) and i.get("status") == "new"]
                in_progress_items = [i for i in items if i.get("status") == "in_progress"]
                done_items = [i for i in items if i.get("status") == "done"]
            else:
                cat_tabs = [st.container()]
                new_items = data.get("items", [])
                assigned_items = []
                in_progress_items = []
                done_items = []

        # Admin panel: assign tickets, manage workers
        if role == "admin":
            st.subheader("Admin: Assign Tickets")
            try:
                all_users = list_users()
                workers = [u for u in all_users if u.get("role") == "worker"]
                worker_options = {f"{w['username']}": w["id"] for w in workers}
            except Exception as e:
                st.error(f"Cannot load users: {e}")
                worker_options = {}

            # Render each category list with assignment controls
            def render_assign_list(items_list, tab_idx: int):
                with cat_tabs[tab_idx]:
                    for item in items_list:
                        is_new_unassigned = item.get("status") == "new" and not item.get("worker")
                        badge = "🟢 NEW · " if is_new_unassigned else ""
                        worker_name = item.get('worker', {}).get('username') if item.get('worker') else 'unassigned'
                        header = f"{badge}#{item['id']} {item['title']} - Worker: {worker_name}"
                        with st.expander(header):
                            st.write(item["description"])
                            if st.button("Ticket info", key=f"info_{item['id']}"):
                                t = item
                                st.markdown("Contact:")
                                st.code(f"{t['client']['name']} <{t['client']['email']}>", language="")
                                st.markdown("Times:")
                                created = t['created_at'][:19].replace('T', ' ') if t['created_at'] else 'None'
                                assigned = t.get('assigned_at')[:19].replace('T', ' ') if t.get('assigned_at') else 'None'
                                in_progress = t.get('in_progress_at')[:19].replace('T', ' ') if t.get('in_progress_at') else 'None'
                                done = t.get('done_at')[:19].replace('T', ' ') if t.get('done_at') else 'None'
                                st.code(
                                    f"created: {created}\nassigned: {assigned}\nin_progress: {in_progress}\ndone: {done}",
                                    language="",
                                )
                                st.markdown("Requester:")
                                st.code(f"ip: {t.get('requester_ip')}", language="")
                            sel = st.selectbox(
                                "Assign to worker",
                                list(worker_options.keys()) if worker_options else ["No workers"],
                                key=f"assign_sel_{item['id']}",
                            )
                            if worker_options and st.button("Assign", key=f"assign_btn_{item['id']}"):
                                try:
                                    assign_ticket(item["id"], worker_options[sel])
                                    st.success("Assigned")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))

            # Per-tab pagination helpers (slice in UI scope)
            def paged(items_list, tab_key_prefix: str):
                p = int(st.session_state.get(f"{tab_key_prefix}_page") or 1)
                s = int(st.session_state.get(f"{tab_key_prefix}_size") or default_page_size)
                start = (p - 1) * s
                end = start + s
                return items_list[start:end]

            def paginator(items_list, tab_key_prefix: str):
                total = len(items_list)
                s = int(st.session_state.get(f"{tab_key_prefix}_size") or default_page_size)
                pages = max(1, (total + s - 1) // s)
                p = int(st.session_state.get(f"{tab_key_prefix}_page") or 1)
                left, mid, right = st.columns([1, 3, 1])
                with left:
                    if st.button("← Prev", key=f"{tab_key_prefix}_prev", disabled=p <= 1):
                        st.session_state[f"{tab_key_prefix}_page"] = max(1, p - 1)
                        st.rerun()
                with mid:
                    st.markdown(f"Page {p} / {pages}")
                with right:
                    if st.button("Next →", key=f"{tab_key_prefix}_next", disabled=p >= pages):
                        st.session_state[f"{tab_key_prefix}_page"] = min(pages, p + 1)
                        st.rerun()

            with cat_tabs[0]:
                st.session_state["new_size"] = st.number_input("Page size (New)", 1, 100, default_page_size, key="new_size_num")
                render_assign_list(paged(new_items, "new"), 0)
                paginator(new_items, "new")

            with cat_tabs[1]:
                st.session_state["ass_size"] = st.number_input("Page size (Assigned)", 1, 100, default_page_size, key="ass_size_num")
                render_assign_list(paged(assigned_items, "ass"), 1)
                paginator(assigned_items, "ass")

            with cat_tabs[2]:
                st.session_state["prog_size"] = st.number_input("Page size (In Progress)", 1, 100, default_page_size, key="prog_size_num")
                render_assign_list(paged(in_progress_items, "prog"), 2)
                paginator(in_progress_items, "prog")

            with cat_tabs[3]:
                st.session_state["done_size"] = st.number_input("Page size (Done)", 1, 100, default_page_size, key="done_size_num")
                render_assign_list(paged(done_items, "done"), 3)
                paginator(done_items, "done")

            if tab_workers is not None:
                with tab_workers:
                    st.subheader("Workers")
                    # Create worker button
                    if st.button("Create worker", key="open_create_worker"):
                        st.session_state["show_create_worker_dialog"] = True

                    if st.session_state.get("show_create_worker_dialog"):
                        @st.dialog("Create Worker")
                        def create_worker_dialog():
                            username = st.text_input("Username", key="dlg_new_w_username")
                            password = st.text_input("Password", type="password", key="dlg_new_w_password")
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button("Cancel", key="dlg_create_cancel"):
                                    st.session_state["show_create_worker_dialog"] = False
                                    st.rerun()
                            with col2:
                                if st.button("Create", key="dlg_create_submit"):
                                    if not username or not password:
                                        st.error("Username and password required")
                                    else:
                                        try:
                                            create_user(username, password, "worker")
                                            st.success("Worker created")
                                            st.session_state["show_create_worker_dialog"] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(str(e))
                        create_worker_dialog()

                    # Metrics per worker
                    try:
                        all_users = list_users()
                        workers = [u for u in all_users if u.get("role") == "worker"]
                    except Exception as e:
                        st.error(f"Cannot load users: {e}")
                        workers = []

                    # Token in URL for opening new tab
                    base_url = "?"

                    for w in workers:
                        with st.expander(f"{w['username']}"):
                            cols = st.columns([2, 2, 2, 2])
                            # Prefer precise stats endpoint; fallback to list counts
                            try:
                                s = tickets_stats(w["id"])  # exact stats per worker
                                assigned = s.get("assigned", 0)
                                in_prog = s.get("in_progress", 0)
                            except Exception:
                                try:
                                    assigned = list_tickets(page=1, size=1, worker_id=w["id"], status="new").get("total", 0)
                                except Exception:
                                    assigned = 0
                                try:
                                    in_prog = list_tickets(page=1, size=1, worker_id=w["id"], status="in_progress").get("total", 0)
                                except Exception:
                                    in_prog = 0
                            with cols[0]:
                                st.metric("Assigned", assigned)
                            with cols[1]:
                                st.metric("In progress", in_prog)
                            with cols[2]:
                                # View tasks in new tab via short-lived view token (minted for admin)
                                if st.button("View tasks", key=f"view_tasks_{w['id']}"):
                                    try:
                                        vt_resp = httpx.post(f"{API_URL}/auth/request_view_token", headers=auth_headers())
                                        vt_resp.raise_for_status()
                                        vt = vt_resp.json().get("access_token")
                                        link = f"{base_url}mode=worker_tasks&worker_id={w['id']}&vt={vt}"
                                        st.markdown(f"<a href=\"{link}\" target=\"_blank\" rel=\"noopener noreferrer\">Open in new tab</a>", unsafe_allow_html=True)
                                    except Exception as e:
                                        st.error(str(e))
                            with cols[3]:
                                if st.button("Delete", key=f"del_w_{w['id']}"):
                                    try:
                                        delete_user(w["id"]) 
                                        st.success("Deleted")
                                    except Exception as e:
                                        st.error(str(e))

        # Worker panel: my tickets, mark viewed, update status
        if role == "worker":
            st.subheader("Worker: My Tickets")

            worker_tabs = st.tabs(["New", "In Progress", "Done"]) if role == "worker" else [st.container()]

            def render_worker_list(items_list, tab_idx: int):
                with worker_tabs[tab_idx]:
                    for item in items_list:
                        status_badge = "🟢 NEW · " if item.get("status") == "new" else ""
                        header = f"{status_badge}#{item['id']} {item['title']}"
                        with st.expander(header):
                            st.write(item["description"])
                            cols = st.columns(2)
                            with cols[0]:
                                new_status = st.selectbox(
                                    "Update status",
                                    ["new", "in_progress", "done"],
                                    index=["new", "in_progress", "done"].index(item["status"]),
                                    key=f"status_{item['id']}",
                                )
                            with cols[1]:
                                if st.button("Save", key=f"save_{item['id']}"):
                                    try:
                                        update_ticket_status(item["id"], new_status)
                                        st.success("Saved")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(str(e))
                            if st.button("Ticket info", key=f"winfo_{item['id']}"):
                                t = item
                                st.markdown("Contact:")
                                st.code(f"{t['client']['name']} <{t['client']['email']}>", language="")
                                st.markdown("Times:")
                                created = t['created_at'][:19].replace('T', ' ') if t['created_at'] else 'None'
                                assigned = t.get('assigned_at')[:19].replace('T', ' ') if t.get('assigned_at') else 'None'
                                in_progress = t.get('in_progress_at')[:19].replace('T', ' ') if t.get('in_progress_at') else 'None'
                                done = t.get('done_at')[:19].replace('T', ' ') if t.get('done_at') else 'None'
                                st.code(
                                    f"created: {created}\nassigned: {assigned}\nin_progress: {in_progress}\ndone: {done}",
                                    language="",
                                )
                                st.markdown("Requester:")
                                st.code(f"ip: {t.get('requester_ip')}", language="")

            if role == "worker":
                items = data.get("items", [])
                w_new = [i for i in items if i.get("status") == "new"]
                w_prog = [i for i in items if i.get("status") == "in_progress"]
                w_done = [i for i in items if i.get("status") == "done"]

                with worker_tabs[0]:
                    st.session_state["wnew_size"] = st.number_input("Page size (New)", 1, 100, default_page_size, key="wnew_size_num")
                    p = int(st.session_state.get("wnew_page") or 1); s = int(st.session_state["wnew_size"])
                    render_worker_list(w_new[(p-1)*s:p*s], 0)
                    # paginator bottom
                    total = len(w_new); pages = max(1, (total + s - 1)//s)
                    left, mid, right = st.columns([1,3,1])
                    with left:
                        if st.button("← Prev", key="wnew_prev", disabled=p<=1):
                            st.session_state["wnew_page"] = max(1, p-1); st.rerun()
                    with mid:
                        st.markdown(f"Page {p} / {pages}")
                    with right:
                        if st.button("Next →", key="wnew_next", disabled=p>=pages):
                            st.session_state["wnew_page"] = min(pages, p+1); st.rerun()

                with worker_tabs[1]:
                    st.session_state["wprog_size"] = st.number_input("Page size (In Progress)", 1, 100, default_page_size, key="wprog_size_num")
                    p = int(st.session_state.get("wprog_page") or 1); s = int(st.session_state["wprog_size"])
                    render_worker_list(w_prog[(p-1)*s:p*s], 1)
                    total = len(w_prog); pages = max(1, (total + s - 1)//s)
                    left, mid, right = st.columns([1,3,1])
                    with left:
                        if st.button("← Prev", key="wprog_prev", disabled=p<=1):
                            st.session_state["wprog_page"] = max(1, p-1); st.rerun()
                    with mid:
                        st.markdown(f"Page {p} / {pages}")
                    with right:
                        if st.button("Next →", key="wprog_next", disabled=p>=pages):
                            st.session_state["wprog_page"] = min(pages, p+1); st.rerun()

                with worker_tabs[2]:
                    st.session_state["wdone_size"] = st.number_input("Page size (Done)", 1, 100, default_page_size, key="wdone_size_num")
                    p = int(st.session_state.get("wdone_page") or 1); s = int(st.session_state["wdone_size"])
                    render_worker_list(w_done[(p-1)*s:p*s], 2)
                    total = len(w_done); pages = max(1, (total + s - 1)//s)
                    left, mid, right = st.columns([1,3,1])
                    with left:
                        if st.button("← Prev", key="wdone_prev", disabled=p<=1):
                            st.session_state["wdone_page"] = max(1, p-1); st.rerun()
                    with mid:
                        st.markdown(f"Page {p} / {pages}")
                    with right:
                        if st.button("Next →", key="wdone_next", disabled=p>=pages):
                            st.session_state["wdone_page"] = min(pages, p+1); st.rerun()

        st.write(f"Total: {data.get('total')}")


if __name__ == "__main__":
    main()


