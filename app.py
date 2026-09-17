import streamlit as st
from agent import luce_process_message, read_emails
import json

# Configuration de la page
st.set_page_config(
    page_title="Luce - Assistant IA Sécurisé",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    .blocked-message {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .email-item {
        padding: 0.75rem;
        border-bottom: 1px solid #e0e0e0;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .email-item:hover {
        background-color: #f5f5f5;
    }
    .sidebar-button {
        width: 100%;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation de l'état de la session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_view" not in st.session_state:
    st.session_state.current_view = "chat"

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
    st.markdown("### 🛡️ Luce")
    st.markdown("*Assistant IA Sécurisé*")
    st.divider()
    
    # Navigation
    st.markdown("#### Navigation")
    if st.button("💬 Chat", key="chat_btn", use_container_width=True):
        st.session_state.current_view = "chat"
    
    if st.button("📧 Inbox", key="inbox_btn", use_container_width=True):
        st.session_state.current_view = "inbox"
    
    if st.button("🔗 Connexions", key="connections_btn", use_container_width=True):
        st.session_state.current_view = "connections"
    
    st.divider()
    
    # Statistiques de sécurité
    st.markdown("#### 📊 Sécurité")
    blocked_count = sum(1 for msg in st.session_state.messages if msg.get("status") == "BLOCKED")
    allowed_count = sum(1 for msg in st.session_state.messages if msg.get("status") == "ALLOWED")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Autorisées", allowed_count)
    with col2:
        st.metric("Bloquées", blocked_count, delta=None, delta_color="inverse")
    
    st.divider()
    
    # Info
    st.markdown("#### ℹ️ À propos")
    st.markdown("""
    Luce est protégée par **CerbereAG**, un système de sécurité runtime 
    qui détecte et bloque les tentatives d'injection, d'exfiltration 
    et les commandes dangereuses.
    """)

# ==============================================================================
# VUE CHAT
# ==============================================================================
if st.session_state.current_view == "chat":
    st.markdown('<div class="main-header">💬 Chat avec Luce</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Posez vos questions ou demandez à Luce d\'effectuer des tâches administratives</div>', unsafe_allow_html=True)
    
    # Affichage de l'historique
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "status" in message:
                if message["status"] == "BLOCKED":
                    st.error("🛡️ Action bloquée par CerbereAG")
                elif message["status"] == "ALLOWED":
                    st.success("✅ Action autorisée et sécurisée")
    
    # Zone de saisie
    if prompt := st.chat_input("Demandez à Luce de vous aider..."):
        # Ajouter le message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Traiter avec Luce
        with st.chat_message("assistant"):
            with st.spinner("Luce réfléchit..."):
                reply, status = luce_process_message(prompt, st.session_state.messages[:-1])
                st.markdown(reply)
                
                if status == "BLOCKED":
                    st.error("🛡️ Action bloquée par CerbereAG")
                else:
                    st.success("✅ Action autorisée")
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": reply, 
                    "status": status
                })

# ==============================================================================
# VUE INBOX
# ==============================================================================
elif st.session_state.current_view == "inbox":
    st.markdown('<div class="main-header">📧 Inbox Gmail</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Vos emails récents sécurisés par CerbereAG</div>', unsafe_allow_html=True)
    
    if st.button("🔄 Rafraîchir", key="refresh_btn"):
        st.rerun()
    
    # Récupérer les emails
    with st.spinner("Chargement des emails..."):
        emails_result = read_emails(query="inbox", max_results=10)
    
    if emails_result["status"] == "success":
        emails = emails_result["emails"]
        
        if not emails:
            st.info("Aucun email trouvé dans votre boîte de réception.")
        else:
            st.markdown(f"**{len(emails)} emails récents**")
            
            for i, email in enumerate(emails):
                with st.expander(f"📧 {email.get('subject', 'Sans objet')} - {email.get('from', 'Inconnu')}"):
                    st.markdown(f"**De :** {email.get('from', 'N/A')}")
                    st.markdown(f"**Date :** {email.get('date', 'N/A')}")
                    st.markdown(f"**Objet :** {email.get('subject', 'N/A')}")
                    st.divider()
                    st.markdown(email.get('body', 'Pas de contenu'))
                    
                    # Actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📝 Résumer", key=f"summarize_{i}"):
                            st.session_state.current_view = "chat"
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Peux-tu résumer cet email : {email.get('subject', '')}"
                            })
                            st.rerun()
                    with col2:
                        if st.button("↩️ Répondre", key=f"reply_{i}"):
                            st.session_state.current_view = "chat"
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Peux-tu répondre à cet email de {email.get('from', '')} : {email.get('subject', '')}"
                            })
                            st.rerun()
    else:
        st.error(f"Erreur lors du chargement des emails : {emails_result['message']}")

# ==============================================================================
# VUE CONNEXIONS
# ==============================================================================
elif st.session_state.current_view == "connections":
    st.markdown('<div class="main-header">🔗 Connexions</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Gérez les intégrations de Luce avec vos outils</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 📧 Gmail")
        st.success("✅ Connecté")
        st.markdown("Lecture et envoi d'emails")
    
    with col2:
        st.markdown("#### 📅 Google Calendar")
        st.success("✅ Connecté")
        st.markdown("Gestion du calendrier")
    
    with col3:
        st.markdown("#### 📁 Google Drive")
        st.success("✅ Connecté")
        st.markdown("Gestion des fichiers")
    
    st.divider()
    
    st.markdown("#### 🔒 Sécurité")
    st.info("""
    Toutes les connexions sont protégées par **CerbereAG**. 
    Chaque action est analysée en temps réel pour détecter :
    - Tentatives d'injection de prompts
    - Exfiltration de données sensibles
    - Commandes dangereuses
    - Comportements anormaux
    """)

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #999; font-size: 0.9rem;'>
    Propulsé par <strong>CerbereAG</strong> | Runtime Security & Observability for AI Agents
    </div>
    """,
    unsafe_allow_html=True
)
