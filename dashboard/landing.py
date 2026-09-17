"""Authenticated welcome screen for RMIP-DSS."""

import streamlit as st


def landing_page() -> None:
    st.markdown("""
    <style>
    .dash-hero {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.4), rgba(15, 23, 42, 0.3));
        border: 1px solid rgba(51, 65, 85, 0.3);
        border-radius: 12px;
        padding: 2.5rem;
        margin-bottom: 2rem;
    }
    
    .dash-hero h1 {
        font-size: 2.5rem;
        color: #F8FAFC;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        letter-spacing: -1px;
    }
    
    .dash-hero h1 em {
        color: #06B6D4;
        font-style: normal;
    }
    
    .dash-hero p {
        font-size: 1.05rem;
        color: #94A3B8;
        line-height: 1.6;
        margin: 0;
    }
    
    .welcome-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 2rem;
        margin-bottom: 2rem;
    }
    
    .session-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(51, 65, 85, 0.3);
        border-radius: 10px;
        padding: 1.5rem;
    }
    
    .session-card h3 {
        font-size: 0.95rem;
        color: #F8FAFC;
        font-weight: 600;
        margin: 0 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    
    .session-card .user-name {
        font-size: 1.2rem;
        color: #06B6D4;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .session-info {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1rem;
        margin-bottom: 1rem;
    }
    
    .session-info-item {
        background: rgba(15, 23, 42, 0.4);
        border: 1px solid rgba(51, 65, 85, 0.2);
        border-radius: 6px;
        padding: 0.8rem;
    }
    
    .session-info-item label {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: block;
        margin-bottom: 0.3rem;
    }
    
    .session-info-item value {
        font-size: 0.9rem;
        color: #F8FAFC;
        font-weight: 600;
        display: block;
    }
    
    .session-security {
        background: rgba(6, 182, 212, 0.1);
        border: 1px solid rgba(6, 182, 212, 0.2);
        border-radius: 6px;
        padding: 0.8rem;
        font-size: 0.75rem;
        color: #06B6D4;
    }
    
    .action-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .action-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(51, 65, 85, 0.3);
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .action-card:hover {
        background: rgba(30, 41, 59, 0.7);
        border-color: rgba(6, 182, 212, 0.4);
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(6, 182, 212, 0.1);
    }
    
    .action-card .icon {
        font-size: 2.2rem;
        margin-bottom: 0.8rem;
    }
    
    .action-card h3 {
        font-size: 1rem;
        color: #F8FAFC;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }
    
    .action-card p {
        font-size: 0.8rem;
        color: #94A3B8;
        margin: 0;
    }
    
    .capabilities {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .capability-item {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(51, 65, 85, 0.3);
        border-radius: 10px;
        padding: 1.5rem;
    }
    
    .capability-item .icon {
        font-size: 1.6rem;
        color: #06B6D4;
        margin-bottom: 0.6rem;
    }
    
    .capability-item h4 {
        font-size: 0.95rem;
        color: #F8FAFC;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }
    
    .capability-item ul {
        font-size: 0.8rem;
        color: #94A3B8;
        margin: 0;
        padding-left: 1.2rem;
    }
    
    .capability-item li {
        margin-bottom: 0.3rem;
    }
    
    .info-cards {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
    }
    
    .info-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(51, 65, 85, 0.3);
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
    }
    
    .info-card .icon {
        font-size: 1.8rem;
        color: #06B6D4;
        margin-bottom: 0.8rem;
    }
    
    .info-card h4 {
        font-size: 0.95rem;
        color: #F8FAFC;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }
    
    .info-card p {
        font-size: 0.75rem;
        color: #94A3B8;
        margin: 0;
        line-height: 1.4;
    }
    
    @media (max-width: 768px) {
        .welcome-grid, .action-grid, .capabilities, .info-cards {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # ===== HERO SECTION =====
    st.markdown(f"""
    <div class="dash-hero">
        <h1>Welcome back, <em>{st.session_state.user}</em></h1>
        <p>Access powerful portfolio insights, market intelligence, and pricing analytics in one unified dashboard.</p>
    </div>
    """, unsafe_allow_html=True)

    # ===== SESSION INFO + QUICK ACTIONS =====
    col_welcome, col_session = st.columns([2, 1], gap="large")
    
    with col_welcome:
        # Quick action cards
        st.markdown("<div class='action-grid'>", unsafe_allow_html=True)
        action_cols = st.columns(3)
        actions = [
            ("📊", "Open Dashboard", "View portfolio analytics and KPIs"),
            ("📁", "Upload Data", "Add new portfolio datasets"),
            ("📈", "Market Intelligence", "Analyze market trends and benchmarks"),
        ]
        for col, (icon, title, desc) in zip(action_cols, actions):
            with col:
                st.markdown(f"""
                <div class="action-card">
                    <div class="icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Capabilities section
        st.markdown("<h3 style='color: #F8FAFC; font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem;'>What you can do</h3>", unsafe_allow_html=True)
        st.markdown("<div class='capabilities'>", unsafe_allow_html=True)
        cap_cols = st.columns(2)
        capabilities = [
            ("📊", "Portfolio Management", [
                "Upload datasets with flexible column mapping",
                "Filter historical ranges and custom periods",
                "Track premium, claims, and loss ratios"
            ]),
            ("🎯", "Analytics & Insights", [
                "Generate executive summaries",
                "Export actionable reports",
                "Monitor data quality in real time"
            ]),
            ("💼", "Market Intelligence", [
                "Analyze market trends",
                "Benchmark against peers",
                "Identify risk concentration"
            ]),
            ("⚡", "Performance Monitoring", [
                "Track KPIs and metrics",
                "Monitor system health",
                "View audit trails and compliance logs"
            ]),
        ]
        for col, (icon, title, items) in zip(cap_cols, capabilities):
            with col:
                st.markdown(f"""
                <div class="capability-item">
                    <div class="icon">{icon}</div>
                    <h4>{title}</h4>
                    <ul>
                        {"".join(f"<li>{item}</li>" for item in items)}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_session:
        # Session info card
        st.markdown(f"""
        <div class="session-card">
            <h3>👤 Current Session</h3>
            <div class="user-name">{st.session_state.user}</div>
            <div class="session-info">
                <div class="session-info-item">
                    <label>Email</label>
                    <value>{st.session_state.email}</value>
                </div>
                <div class="session-info-item">
                    <label>Role</label>
                    <value>{st.session_state.role}</value>
                </div>
            </div>
            <div class="session-info-item">
                <label>Department</label>
                <value>{st.session_state.department}</value>
            </div>
            <div class="session-security" style="margin-top: 1rem;">
                🔒 <strong>Secure Access</strong><br>All actions are logged and monitored
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ===== BUTTONS SECTION =====
    st.markdown("<h3 style='color: #F8FAFC; font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem;'>Get Started</h3>", unsafe_allow_html=True)
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    
    with btn_col1:
        if st.button("📊 Dashboard", use_container_width=True, type="primary", help="View analytics"):
            st.session_state.page = "dashboard"
            st.session_state.dashboard_section = "Executive overview"
            st.rerun()
    
    with btn_col2:
        if st.button("📁 Upload Data", use_container_width=True, help="Add datasets"):
            st.session_state.page = "dashboard"
            st.session_state.dashboard_section = "Upload data"
            st.rerun()
    
    with btn_col3:
        if st.button("⚙️ Settings", use_container_width=True, help="Profile settings"):
            st.session_state.page = "dashboard"
            st.session_state.dashboard_section = "Settings"
            st.rerun()
    
    with btn_col4:
        if st.button("🚪 Log Out", use_container_width=True, help="End session"):
            for key in ("logged_in", "user", "email", "role", "department", "page"):
                st.session_state.pop(key, None)
            st.rerun()

    st.divider()

    # ===== INFO SECTION =====
    st.markdown("<h3 style='color: #F8FAFC; font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem;'>Why Acentria</h3>", unsafe_allow_html=True)
    st.markdown("<div class='info-cards'>", unsafe_allow_html=True)
    info_cols = st.columns(3)
    info_items = [
        ("🔐", "Enterprise Security", "SOC 2 Type II compliant • Role-based access • Audit trails"),
        ("⚡", "Real-time Intelligence", "Premium, claims & risk data unified • Sub-second queries"),
        ("🎯", "Decisive Action", "Clear insights • Strategic reporting • Custom dashboards"),
    ]
    for col, (icon, title, desc) in zip(info_cols, info_items):
        with col:
            st.markdown(f"""
            <div class="info-card">
                <div class="icon">{icon}</div>
                <h4>{title}</h4>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

