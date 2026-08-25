"""
Escape room — prezent-niespodzianka.

Jak to działa: kilka etapów z zagadkami, każdy odsłania jedną cyfrę kodu
do fizycznego sejfu. Wszystko, co trzeba zmienić, jest w sekcji
KONFIGURACJA poniżej — reszta pliku działa "z automatu".

Postęp zapisuje się automatycznie (w adresie URL i w pliku na serwerze),
więc jeśli ona zamknie telefon w połowie gry i wróci później (np. po
dojechaniu na miejsce z etapu w realu), aplikacja sama wznowi dokładnie
tam, gdzie skończyła — nie musi niczego wpisywać.

Uruchomienie lokalne:   streamlit run app.py
Instalacja zależności:  pip install -r requirements.txt

WAŻNE — reset postępu podczas testowania: otwórz aplikację z dopiskiem
?resetuj=tak na końcu adresu (np. https://twoja-appka.streamlit.app/?resetuj=tak).
Zrób to RAZ, tuż przed przekazaniem prezentu, żeby wyczyścić swoje testy —
inaczej dasz jej wersję, która "pamięta", że Ty już wszystko rozwiązałeś.
"""

import json
import os
import time

import streamlit as st
import streamlit.components.v1 as components

# ======================================================================
# 🔧🔧🔧  KONFIGURACJA — TU WSZYSTKO ZMIENIASZ NA SWOJE  🔧🔧🔧
# ======================================================================

IMIE = "Kochanie"  # <- imię Twojej dziewczyny

WIADOMOSC_POWITALNA = """
Witaj w grze, którą przygotowałem specjalnie dla Ciebie.

Czeka na Ciebie **kilka etapów**. Za każdy poprawnie rozwiązany dostaniesz
jedną cyfrę. Zbierz je wszystkie, a otworzysz nimi coś, co czeka na Ciebie
naprawdę. Możesz korzystać z dowolnej pomocy, jakiej tylko chcesz —
Google, znajomych, czego chcesz. Powodzenia. 🖤
"""

WIADOMOSC_KONCOWA = """
Udało Ci się rozwiązać wszystko.

To był mój sposób, żeby Ci powiedzieć, jak wiele dla mnie znaczysz — nie
chciałem Ci tego po prostu powiedzieć, chciałem, żebyś to **poczuła**,
etap po etapie. Kod do sejfu jest poniżej. To, co w środku, czeka już
naprawdę na Ciebie. Kocham Cię. ❤️
"""

# Trudność mini-gry zręcznościowej
GRA_CEL = 12       # ile serc trzeba złapać, żeby wygrać
GRA_CZAS = 20       # ile sekund trwa gra
KOD_GRY = "4821"    # kod, który gra pokaże po wygranej (dowolny — może być np. Wasza data)

# ETAPY — kolejność ma znaczenie! Każdy etap daje JEDNĄ cyfrę kodu do sejfu.
# Ile etapów, tyle cyfr w kodzie — dopasuj długość listy do swojej kłódki
# (po prostu skopiuj/usuń któryś słownik).
ETAPY = [
    {
        "klucz": "gra",
        "tytul": "🖤 Etap 1 — Refleks",
        "typ": "gra",
        "opis": "Złap wystarczająco serc ❤️, unikaj bomb 💣. Kod pojawi się po wygranej.",
        "odpowiedz": KOD_GRY,
        "cyfra": "7",
    },
    {
        "klucz": "quiz",
        "tytul": "💭 Etap 2 — Ile mnie znasz?",
        "typ": "quiz",
        "prog": 1.0,  # 1.0 = wymagane 100% poprawnych odpowiedzi
        "pytania": [
            {
                "pytanie": "UZUPEŁNIJ np.: W jakim mieście był nasz pierwszy wspólny wyjazd?",
                "opcje": ["UZUPEŁNIJ opcję A", "UZUPEŁNIJ opcję B", "UZUPEŁNIJ opcję C"],
                "poprawna": 0,
            },
            {
                "pytanie": "UZUPEŁNIJ kolejne pytanie o Was...",
                "opcje": ["Opcja A", "Opcja B", "Opcja C"],
                "poprawna": 1,
            },
            # dodaj tyle pytań ile chcesz — po prostu kopiuj wzór powyżej
        ],
        "cyfra": "3",
    },
    {
        "klucz": "jezyk",
        "tytul": "🐦 Etap 3 — Po ptakach",
        "typ": "haslo",
        "tresc": (
            "### AFTER BIRDS\n\n"
            "To nie jest prawdziwy angielski zwrot... a jednak coś powinno Ci "
            "zaświtać, jeśli przetłumaczysz to na nasze, słowo w słowo.\n\n"
            "Wpisz to polskie wyrażenie (dwa słowa):"
        ),
        "odpowiedz": "po ptakach",
        "cyfra": "9",
    },
    {
        "klucz": "wordle",
        "tytul": "🟩 Etap 4 — Wordle dnia",
        "typ": "haslo",
        "tresc": (
            "Zagraj dzisiaj w Wordle (np. na nytimes.com/games/wordle) "
            "i wpisz słowo, które dziś odgadłaś:"
        ),
        "odpowiedz": "UZUPEŁNIJ",  # <- wpisz słowo z Wordle na dzień, w którym dajesz prezent!
        "cyfra": "1",
    },
    {
        "klucz": "irl",
        "tytul": "📍 Etap 5 — Wyprawa",
        "typ": "haslo",
        "tresc": "UZUPEŁNIJ: opisz konkretne miejsce i co ma tam znaleźć / sprawdzić.",
        "odpowiedz": "UZUPEŁNIJ",
        "cyfra": "5",
    },
]

PLIK_STANU = "stan_gry.json"

# ======================================================================
# SZABLON MINI-GRY (HTML/CSS/JS) — nie musisz tu nic zmieniać
# ======================================================================

SZABLON_GRY = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; user-select: none; }
  body {
    margin: 0;
    font-family: -apple-system, 'Poppins', sans-serif;
    background: radial-gradient(circle at 50% 0%, #241b3a 0%, #0d0d0d 70%);
    overflow: hidden;
  }
  #panel {
    display: flex;
    justify-content: space-between;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 410px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
  }
  .item {
    position: absolute;
    top: -60px;
    font-size: 32px;
    cursor: pointer;
    animation-name: spadanie;
    animation-timing-function: linear;
    animation-fill-mode: forwards;
  }
  @keyframes spadanie {
    from { transform: translateY(0); }
    to { transform: translateY(470px); }
  }
  #wynikEkran {
    display: none;
    position: absolute;
    inset: 0;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 20px;
  }
  #wynikEkran h2 { font-size: 24px; margin-bottom: 6px; }
  #kodWygrany {
    font-size: 28px;
    letter-spacing: 4px;
    color: #fff;
    background: #1a1a2e;
    padding: 8px 18px;
    border-radius: 10px;
    border: 1px solid #d4af37;
    margin: 10px 0;
  }
  button.gra-btn {
    background: linear-gradient(135deg,#e6c15c,#d4af37);
    border: none;
    padding: 10px 22px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 6px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span>❤️ <span id="wynik">0</span> / __CEL__</span>
    <span>⏱️ <span id="czas">__CZAS__</span>s</span>
  </div>
  <div id="gra">
    <div id="wynikEkran">
      <h2 id="wynikTytul"></h2>
      <p id="wynikOpis"></p>
      <div id="kodBox" style="display:none;">
        <div id="kodWygrany">__KOD_GRY__</div>
        <p style="opacity:0.7; font-size:13px;">Przepisz ten kod poniżej 👇</p>
      </div>
      <button class="gra-btn" onclick="startGry()" id="resetBtn">Zagraj ponownie</button>
    </div>
  </div>

<script>
  var CEL = __CEL__;
  var CZAS_START = __CZAS__;
  var wynik = 0;
  var pozostalyCzas = CZAS_START;
  var interwalSpawn, interwalCzas;
  var trwa = false;

  var gra = document.getElementById('gra');
  var wynikEl = document.getElementById('wynik');
  var czasEl = document.getElementById('czas');
  var wynikEkran = document.getElementById('wynikEkran');
  var wynikTytul = document.getElementById('wynikTytul');
  var wynikOpis = document.getElementById('wynikOpis');
  var kodBox = document.getElementById('kodBox');
  var resetBtn = document.getElementById('resetBtn');

  function losowo(min, max) { return Math.random() * (max - min) + min; }

  function stworzElement() {
    var el = document.createElement('div');
    var zly = Math.random() < 0.28;
    el.className = 'item';
    el.textContent = zly ? '💣' : '❤️';
    el.style.left = losowo(5, 82) + '%';
    var czasSpadania = losowo(2.2, 3.6);
    el.style.animationDuration = czasSpadania + 's';
    el.addEventListener('click', function () { kliknieto(el, zly); });
    el.addEventListener('touchstart', function (e) { e.preventDefault(); kliknieto(el, zly); }, { passive: false });
    el.addEventListener('animationend', function () { el.remove(); });
    gra.appendChild(el);
  }

  function kliknieto(el, zly) {
    if (!trwa || el.dataset.klik) return;
    el.dataset.klik = "1";
    el.remove();
    if (zly) {
      wynik = Math.max(0, wynik - 1);
    } else {
      wynik += 1;
    }
    wynikEl.textContent = wynik;
    if (wynik >= CEL) {
      zakoncz(true);
    }
  }

  function tik() {
    pozostalyCzas -= 1;
    czasEl.textContent = pozostalyCzas;
    if (pozostalyCzas <= 0) {
      zakoncz(false);
    }
  }

  function zakoncz(wygrana) {
    trwa = false;
    clearInterval(interwalSpawn);
    clearInterval(interwalCzas);
    var elementy = gra.querySelectorAll('.item');
    elementy.forEach(function (e) { e.remove(); });
    wynikEkran.style.display = 'flex';
    if (wygrana) {
      wynikTytul.textContent = '🎉 Wygrałaś!';
      wynikOpis.textContent = 'Twój kod czeka poniżej:';
      kodBox.style.display = 'block';
      resetBtn.style.display = 'none';
    } else {
      wynikTytul.textContent = 'Prawie!';
      wynikOpis.textContent = 'Złapałaś ' + wynik + ' / ' + CEL + '. Spróbuj jeszcze raz!';
      kodBox.style.display = 'none';
      resetBtn.style.display = 'inline-block';
    }
  }

  function startGry() {
    wynik = 0;
    pozostalyCzas = CZAS_START;
    wynikEl.textContent = 0;
    czasEl.textContent = pozostalyCzas;
    wynikEkran.style.display = 'none';
    trwa = true;
    interwalSpawn = setInterval(stworzElement, 550);
    interwalCzas = setInterval(tik, 1000);
  }

  startGry();
</script>
</body>
</html>
"""

# ======================================================================
# STYL APLIKACJI
# ======================================================================

def wstaw_styl():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Poppins:wght@400;500;600;700&display=swap');

#MainMenu, footer, header {visibility: hidden;}

.stApp {
    background: radial-gradient(circle at 50% -10%, #241b3a 0%, #0d0d0d 55%, #050505 100%);
    color: #f5f5f0;
    font-family: 'Poppins', sans-serif;
}

h1, h2, h3 { font-family: 'Cinzel', serif !important; color: #f0dfa8; }

.tytul {
    font-family: 'Cinzel', serif;
    text-align: center;
    background: linear-gradient(135deg, #e6c15c, #d4af37);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: pojaw 0.9s ease;
}

@keyframes pojaw {
    from { opacity: 0; transform: translateY(-12px); }
    to { opacity: 1; transform: translateY(0); }
}

.zamek-ikona {
    font-size: 3.4rem;
    text-align: center;
    animation: pulsuj 2s ease-in-out infinite;
}
@keyframes pulsuj {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}

.zamek-otwarty {
    font-size: 3.4rem;
    text-align: center;
    animation: otworz 0.7s ease;
}
@keyframes otworz {
    0% { transform: rotate(0deg) scale(0.4); opacity: 0; }
    60% { transform: rotate(-14deg) scale(1.15); opacity: 1; }
    100% { transform: rotate(0deg) scale(1); }
}

.cyfra-tarcza {
    width: 2.8rem;
    height: 3.4rem;
    background: linear-gradient(180deg, #2a2a3d, #16131f);
    border: 2px solid #d4af37;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'Cinzel', serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #e6c15c;
    box-shadow: inset 0 2px 5px rgba(0,0,0,0.6), 0 0 12px rgba(212,175,55,0.35);
}

div.stButton > button {
    background: linear-gradient(135deg, #e6c15c, #d4af37);
    color: #16130a;
    border: none;
    border-radius: 30px;
    padding: 0.55rem 1.4rem;
    font-weight: 700;
    transition: all 0.25s ease;
    width: 100%;
}
div.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 0 18px rgba(212,175,55,0.55);
}

.stTextInput input {
    border-radius: 12px !important;
    border: 1px solid #d4af37 !important;
    background: #1a1a2e !important;
    color: #f5f5f0 !important;
}

.stProgress > div > div {
    background-image: linear-gradient(135deg, #e6c15c, #d4af37);
}

[data-testid="stExpander"] {
    border: 1px solid rgba(212,175,55,0.35);
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# ======================================================================
# TRWAŁY STAN — przetrwa zamknięcie telefonu i wznowienie po jakimś czasie.
# Zapisywany w DWÓCH miejscach naraz (link + plik na serwerze), żeby
# działało niezależnie od tego, czy wraca do tej samej karty przeglądarki,
# czy otwiera link/QR jeszcze raz od zera.
# ======================================================================

def wczytaj_zapisany_stan():
    if os.path.exists(PLIK_STANU):
        try:
            with open(PLIK_STANU, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def zapisz_postep():
    st.query_params["e"] = str(st.session_state.etap)
    if st.session_state.czas_startu:
        st.query_params["t"] = str(st.session_state.czas_startu)
    dane = {"etap": st.session_state.etap, "czas_startu": st.session_state.czas_startu}
    try:
        with open(PLIK_STANU, "w", encoding="utf-8") as f:
            json.dump(dane, f)
    except Exception:
        pass


def zainicjuj_stan():
    if "etap" in st.session_state:
        return

    etap_z_url, czas_z_url = 0, None
    e = st.query_params.get("e")
    if e is not None:
        try:
            etap_z_url = int(e)
        except ValueError:
            etap_z_url = 0
    t = st.query_params.get("t")
    if t is not None:
        try:
            czas_z_url = float(t)
        except ValueError:
            czas_z_url = None

    zapisane = wczytaj_zapisany_stan() or {}
    etap_z_pliku = zapisane.get("etap", 0)
    czas_z_pliku = zapisane.get("czas_startu")

    st.session_state.etap = max(etap_z_url, etap_z_pliku)
    st.session_state.czas_startu = czas_z_url or czas_z_pliku
    st.session_state.aktualny_rozwiazany = False

    if st.session_state.etap > 0:
        zapisz_postep()  # zsynchronizuj URL i plik na wybraną (najdalszą) wartość


def wznow_z_kodu(kod):
    kod = kod.strip().lower()
    if not kod:
        return False
    for i, etap_dane in enumerate(ETAPY):
        oczekiwana = str(etap_dane.get("odpowiedz", "")).strip().lower()
        if oczekiwana and oczekiwana == kod:
            st.session_state.etap = i + 2
            st.session_state.aktualny_rozwiazany = False
            if st.session_state.czas_startu is None:
                st.session_state.czas_startu = time.time()
            zapisz_postep()
            return True
    return False


# ======================================================================
# EKRANY
# ======================================================================

def pokaz_powitanie():
    st.markdown("<div class='zamek-ikona'>🔒</div>", unsafe_allow_html=True)
    st.markdown(f"<h1 class='tytul'>Cześć, {IMIE}</h1>", unsafe_allow_html=True)
    st.markdown(WIADOMOSC_POWITALNA)

    if st.button("Rozpocznij 🔓", key="start_btn"):
        st.session_state.etap = 1
        st.session_state.czas_startu = time.time()
        zapisz_postep()
        st.rerun()

    with st.expander("Coś nie działa? Wpisz swój ostatni zdobyty kod"):
        kod_wznow = st.text_input("Kod:", key="wznow_input")
        if st.button("Wznów", key="wznow_btn"):
            if wznow_z_kodu(kod_wznow):
                st.rerun()
            else:
                st.error("Nie rozpoznaję tego kodu.")


def renderuj_haslo(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(etap_dane["tresc"])

    wpisane = st.text_input("Twoja odpowiedź:", key=f"pole_{klucz}")
    if st.button("Sprawdź", key=f"btn_{klucz}"):
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error("To nie to. Spróbuj jeszcze raz.")
    return False


def renderuj_quiz(etap_dane):
    klucz = etap_dane["klucz"]
    placeholder = "— wybierz —"
    odpowiedzi = []
    for idx, pytanie in enumerate(etap_dane["pytania"]):
        wybor = st.radio(
            pytanie["pytanie"],
            [placeholder] + pytanie["opcje"],
            key=f"{klucz}_pyt_{idx}",
        )
        odpowiedzi.append(wybor)

    if st.button("Sprawdź", key=f"btn_{klucz}"):
        poprawne = 0
        for idx, pytanie in enumerate(etap_dane["pytania"]):
            oczekiwana = pytanie["opcje"][pytanie["poprawna"]]
            if odpowiedzi[idx] == oczekiwana:
                poprawne += 1
        wymagany_prog = etap_dane.get("prog", 1.0)
        procent = poprawne / len(etap_dane["pytania"])
        if procent >= wymagany_prog:
            return True
        st.warning(f"Poprawnych: {poprawne}/{len(etap_dane['pytania'])}. Spróbuj jeszcze raz!")
    return False


def renderuj_gra(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(etap_dane.get("opis", ""))

    html = (
        SZABLON_GRY
        .replace("__CEL__", str(GRA_CEL))
        .replace("__CZAS__", str(GRA_CZAS))
        .replace("__KOD_GRY__", str(KOD_GRY))
    )
    components.html(html, height=500, scrolling=False)

    st.caption("Kiedy wygrasz, przepisz kod z gry poniżej:")
    wpisane = st.text_input("Kod z gry:", key=f"pole_{klucz}")
    if st.button("Sprawdź", key=f"btn_{klucz}"):
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error("To nie ten kod. Zagraj jeszcze raz i sprawdź uważnie!")
    return False


def pokaz_sukces(etap_dane):
    st.success(f"✅ Świetnie! Twoja cyfra to: **{etap_dane['cyfra']}** — zapamiętaj lub zapisz ją!")
    if st.button("Dalej ➜", key=f"dalej_{etap_dane['klucz']}"):
        st.session_state.etap += 1
        st.session_state.aktualny_rozwiazany = False
        zapisz_postep()
        st.rerun()


def pokaz_final():
    st.balloons()
    st.markdown("<div class='zamek-otwarty'>🔓</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='tytul'>Udało się!</h1>", unsafe_allow_html=True)
    st.markdown(WIADOMOSC_KONCOWA)

    kod_koncowy = "".join(str(e["cyfra"]) for e in ETAPY)
    tarcze = "".join(f"<div class='cyfra-tarcza'>{c}</div>" for c in kod_koncowy)
    st.markdown(
        f"""
        <div style='text-align:center; margin-top:1.5rem;'>
          <div style='font-size:0.95rem; opacity:0.75; margin-bottom:0.6rem;'>Kod do sejfu:</div>
          <div style='display:flex; justify-content:center; gap:0.5rem;'>{tarcze}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.czas_startu:
        minuty = (time.time() - st.session_state.czas_startu) / 60
        st.caption(f"⏱️ Ukończone w {minuty:.1f} min")


# ======================================================================
# GŁÓWNA LOGIKA
# ======================================================================

def main():
    st.set_page_config(page_title=f"Dla {IMIE}", page_icon="🔒", layout="centered")
    wstaw_styl()

    if st.query_params.get("resetuj") == "tak":
        if os.path.exists(PLIK_STANU):
            os.remove(PLIK_STANU)
        st.session_state.clear()
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()

    zainicjuj_stan()

    etap = st.session_state.etap

    if etap == 0:
        pokaz_powitanie()
    elif ETAPY and etap <= len(ETAPY):
        etap_dane = ETAPY[etap - 1]

        st.markdown(f"<h2 class='tytul' style='font-size:1.5rem;'>{etap_dane['tytul']}</h2>", unsafe_allow_html=True)
        st.progress(etap / len(ETAPY))
        st.caption(f"Etap {etap} z {len(ETAPY)}")

        if st.session_state.aktualny_rozwiazany:
            pokaz_sukces(etap_dane)
        else:
            typ = etap_dane["typ"]
            if typ == "haslo":
                ok = renderuj_haslo(etap_dane)
            elif typ == "quiz":
                ok = renderuj_quiz(etap_dane)
            elif typ == "gra":
                ok = renderuj_gra(etap_dane)
            else:
                ok = False

            if ok:
                st.session_state.aktualny_rozwiazany = True
                st.balloons()
                st.rerun()
    else:
        pokaz_final()


if __name__ == "__main__":
    main()
