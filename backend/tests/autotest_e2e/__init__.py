"""Autotest E2E framework per SCO Compliance OS desktop app.

Pattern Conv. 46 SMOKE TEST E2E PRIMA DEL TAG: questo modulo fornisce script
Python autonomo che simula end-to-end l'interazione utente sul backend live,
PRIMA di chiedere ad Antonio il test manuale.

I test sono auto-contenuti:
    1. License activation
    2. Onboarding completo (EULA + Privacy + Demo + Tutorial)
    3. Vault register/scaffold
    4. os-setup conversation auto-creata
    5. Simulazione risposte Q1-Q10 al widget ASK_USER_QUESTION
    6. Verifica profile DB populated
    7. New chat task -> verifica widget skill proposal
    8. Memory recall test (2 chat sequenziali)

Pattern Conv. 41 tracciatura: ogni step PASS/FAIL loggato con dettagli.
Pattern Conv. 47 single source of truth: tutti i check fatti via REST API,
mai da memoria React in-app o stato lato frontend.
"""
