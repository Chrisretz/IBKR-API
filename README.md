# 📊 Finansielt Dashboard

Et interaktivt finansielt dashboard bygget i **Streamlit**.

## 🚀 Funktioner
- **Aktiekursgraf** med glidende gennemsnit (SMA50 og SMA200)
- Mulighed for at tilføje **volumen** på sekundær akse
- **Volatility surface** for valgfri aktie (3D interaktiv + 2D contour)
- Responsivt layout, der tilpasser sig skærmen

## 🌐 Live Demo
👉 [Åbn appen her](https://finance-dashboard.streamlit.app)

*(Linket kræver, at du har deployet appen på Streamlit Community Cloud og bruger det valgte app-navn)*

## 🛠 Installation og lokal kørsel
Vil du køre projektet lokalt, så gør følgende:

```bash
git clone https://github.com/Chrisretz/IBKR-API.git
cd IBKR-API
pip install -r requirements.txt
streamlit run finance_dashboard.py
