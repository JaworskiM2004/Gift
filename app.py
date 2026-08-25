"""
Escape room — prezent-niespodzianka.

Jak to działa: etapy do wyboru z menu (w dowolnej kolejności). Za każdy
rozwiązany zapala się zielone światełko. Cały kod do sejfu pokazuje się
DOPIERO gdy wszystko jest rozwiązane. Uważaj na błędy — jest wspólny
"licznik" w postaci wisielca; jeśli dobije do końca, wszystko resetuje
się od zera. Wszystko, co trzeba zmienić, jest w sekcji KONFIGURACJA
poniżej — reszta pliku działa "z automatu".

Postęp zapisuje się automatycznie (w adresie URL i w pliku na serwerze),
więc jeśli zamknie telefon w połowie i wróci później, aplikacja sama
wznowi tam, gdzie było — nie trzeba niczego wpisywać ręcznie.

Uruchomienie lokalne:   streamlit run app.py
Instalacja zależności:  pip install -r requirements.txt

WAŻNE — reset postępu podczas testowania: otwórz aplikację z dopiskiem
?resetuj=tak na końcu adresu (np. https://twoja-appka.streamlit.app/?resetuj=tak).
Zrób to RAZ, tuż przed przekazaniem prezentu, żeby wyczyścić swoje testy.
"""

import json
import os
import time
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

# ======================================================================
# 🔧🔧🔧  KONFIGURACJA — TU WSZYSTKO ZMIENIASZ NA SWOJE  🔧🔧🔧
# ======================================================================

IMIE = "Kochanie"  # <- imię Twojej dziewczyny

POWITANIE_TYTUL = {"pl": f"Cześć, {IMIE}", "en": f"Hi, {IMIE}"}

WIADOMOSC_POWITALNA = {
    "pl": """
Witaj w grze, którą przygotowałem specjalnie dla Ciebie.

Etapy możesz robić w DOWOLNEJ kolejności — wybierasz je z menu. Za każdy
rozwiązany zapala się zielone światełko. Cały kod do sejfu zobaczysz
dopiero, gdy rozwiążesz wszystko.

Uważaj na pomyłki — jest wspólny licznik błędów w postaci wisielca.
Jeśli dobije do końca, wszystko zaczynasz od nowa. Możesz korzystać
z dowolnej pomocy, jakiej chcesz — Google, znajomych, czego chcesz.
Powodzenia. 🖤
""",
    "en": """
Welcome to the game I made just for you.

You can do the stages in ANY order — pick them from the menu. Each
solved one turns green. You'll only see the full safe code once
everything is solved.

Watch out for mistakes — there's a shared mistake counter shown as a
hangman. If it's completed, everything starts over. You can use any
help you want — Google, friends, whatever you need.
Good luck. 🖤
""",
}

WIADOMOSC_KONCOWA = {
    "pl": """
Udało Ci się rozwiązać wszystko.

To był mój sposób, żeby Ci powiedzieć, jak wiele dla mnie znaczysz — nie
chciałem Ci tego po prostu powiedzieć, chciałem, żebyś to **poczuła**,
etap po etapie. Kod do sejfu jest poniżej. To, co w środku, czeka już
naprawdę na Ciebie. Kocham Cię. ❤️
""",
    "en": """
You solved everything.

This was my way of telling you how much you mean to me — I didn't want
to just say it, I wanted you to **feel** it, stage by stage. The safe
code is below. What's inside is really waiting for you now.
I love you. ❤️
""",
}

KOD_GRY = "4821"    # kod, który mini-gra pokaże po ukończeniu wszystkich poziomów

# Trudność mini-gry zręcznościowej — 3 poziomy, coraz trudniejsze.
POZIOMY_GRY = [
    {"serca": 6, "czarne": 2, "kierunek": "dol", "predkosc": 130, "tempo": 650},
    {"serca": 8, "czarne": 4, "kierunek": "skos", "predkosc": 190, "tempo": 480},
    {"serca": 10, "czarne": 6, "kierunek": "gora", "predkosc": 230, "tempo": 340},
]

# Pozycja szachowa (białe zaczynają) — ręcznie zweryfikowana (patrz komentarz
# niżej), ale WARTO sprawdzić samemu: wklej FEN na lichess.org/analysis
# FEN: 7k/6pp/5N2/8/3Q4/8/8/1K6 w - - 0 1
# Rozwiązanie: Qd4-d8# (król na h8 jest zablokowany własnymi pionkami g7/h7,
# a pole g8 kryje skoczek f6 — to jedyna dostępna ucieczka).
POZYCJA_SZACHOWA = {
    "h8": "♚", "g7": "♟", "h7": "♟",
    "b1": "♔", "d4": "♕", "f6": "♘",
}

# ETAPY — każdy daje JEDNĄ cyfrę kodu do sejfu, ale cyfry pokazują się
# dopiero na ekranie końcowym, po rozwiązaniu WSZYSTKIEGO.
ETAPY = [
    {
        "klucz": "gra",
        "tytul": {"pl": "🖤 Refleks", "en": "🖤 Reflexes"},
        "typ": "gra",
        "opis": {
            "pl": "Złap WSZYSTKIE kolorowe serca w każdym z 3 poziomów. Uważaj na czarne — jedna pomyłka i wracasz na początek poziomu.",
            "en": "Catch ALL the colored hearts in each of the 3 levels. Watch out for black ones — one mistake and you restart the level.",
        },
        "odpowiedz": KOD_GRY,
        "cyfra": "7",
    },
    {
        "klucz": "quiz",
        "tytul": {"pl": "💭 Ile mnie znasz?", "en": "💭 How well do you know me?"},
        "typ": "quiz",
        "prog": 1.0,  # 1.0 = wymagane 100% poprawnych odpowiedzi
        "pytania": [
            {
                "pytanie": "UZUPEŁNIJ np.: W jakim mieście był nasz pierwszy wspólny wyjazd?",
                "opcje": ["UZUPEŁNIJ opcję A", "UZUPEŁNIJ opcję B", "UZUPEŁNIJ opcję C"],
                "poprawna": 0,
            },
            {
                # Uwaga: wiek Zoe wg lore LoL jest niejednoznaczny między źródłami
                # (różne wiki podają 1398-1548 lat / "ponad tysiąc lat" / inne ramy) —
                # dopisz dokładną liczbę/opcje, które Ty uznajesz za poprawne.
                "pytanie": "Ile lat (wg lore) ma Zoe z League of Legends?",
                "opcje": ["UZUPEŁNIJ — Twoja poprawna wersja", "UZUPEŁNIJ opcję B", "UZUPEŁNIJ opcję C"],
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
        "tytul": {"pl": "🐦 Po ptakach", "en": "🐦 Po ptakach"},
        "typ": "haslo",
        # Ta zagadka jest o polskim idiomie, więc treść zostaje po polsku
        # niezależnie od wybranego języka aplikacji.
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
        "tytul": {"pl": "🟩 Wordle dnia", "en": "🟩 Today's Wordle"},
        "typ": "haslo",
        "tresc": {
            "pl": "Zagraj dzisiaj w Wordle (np. na nytimes.com/games/wordle) i wpisz słowo, które dziś odgadłaś:",
            "en": "Play today's Wordle (e.g. on nytimes.com/games/wordle) and type the word you guessed today:",
        },
        "odpowiedz": "UZUPEŁNIJ",  # <- wpisz słowo z Wordle na dzień, w którym dajesz prezent! (np. "click")
        "cyfra": "1",
    },
    {
        "klucz": "irl",
        "tytul": {"pl": "📍 Wyprawa", "en": "📍 The trip"},
        "typ": "haslo",
        "tresc": {
            "pl": "UZUPEŁNIJ: opisz konkretne miejsce i co ma tam znaleźć / sprawdzić.",
            "en": "FILL IN: describe a specific place and what she needs to find / check there.",
        },
        "odpowiedz": "UZUPEŁNIJ",
        "cyfra": "5",
    },
    {
        "klucz": "data",
        "tytul": {"pl": "📅 Dokładna data", "en": "📅 The exact date"},
        "typ": "data",
        "tresc": {
            "pl": "Jaka jest dokładna data, kiedy pierwszy raz jechałaś ze mną samochodem?",
            "en": "What's the exact date of the first time you rode in a car with me?",
        },
        "data": date(2026, 2, 24),
        "jedna_proba": True,
        "cyfra": "6",
    },
    {
        "klucz": "szachy",
        "tytul": {"pl": "♟️ Szachy", "en": "♟️ Chess"},
        "typ": "szachy",
        "tresc": {
            "pl": "Białe zaczynają. Znajdź ruch, który wymusza mata.",
            "en": "White to move. Find the move that forces checkmate.",
        },
        "pozycja": POZYCJA_SZACHOWA,
        "odpowiedz": "d4d8",
        "cyfra": "8",
    },
]

PLIK_STANU = "stan_gry.json"

# ======================================================================
# TEKSTY INTERFEJSU (PL / EN)
# ======================================================================

TEKST = {
    "pl": {
        "rozpocznij": "Rozpocznij 🔓",
        "wroc_do_menu": "⬅ Powrót do menu",
        "sprawdz": "Sprawdź",
        "zatwierdz": "Zatwierdź (jedna próba!)",
        "twoja_odpowiedz": "Twoja odpowiedź:",
        "wybierz": "— wybierz —",
        "zle_sprobuj": "To nie to. Spróbuj jeszcze raz.",
        "zle_jedna_proba": "To nie ta data. Ta zagadka jest już zamknięta — była tylko jedna próba.",
        "wybierz_date": "Wybierz datę:",
        "jedna_proba_info": "⚠️ Masz tylko JEDNĄ próbę — wybierz uważnie.",
        "wybierz_najpierw": "Najpierw wybierz datę.",
        "poprawnych": "Poprawnych",
        "twoj_ruch": "Twój ruch:",
        "format_ruchu": "Wpisz ruch jako pole-startowe + pole-docelowe, np. `e2e4`.",
        "kod_z_gry_info": "Kiedy wygrasz wszystkie 3 poziomy, przepisz kod z gry poniżej:",
        "kod_z_gry_label": "Kod z gry:",
        "zle_kod_gry": "To nie ten kod. Zagraj jeszcze raz i sprawdź uważnie!",
        "rozwiazane_status": "✅ Rozwiązane",
        "zamkniete_status": "🔒 Zamknięte (zła próba — jedna szansa już wykorzystana)",
        "menu_tytul": "Wybierz etap",
        "wszystko_rozwiazane": "🎉 Rozwiązałaś wszystko!",
        "zobacz_kod": "Zobacz kod do sejfu 🔓",
        "przegrana_tytul": "Koniec gry",
        "przegrana_wiadomosc": "Pozdro, poćwicz 😏\n\nWisielec dobił do końca — wszystko zaczynasz od nowa.",
        "zacznij_od_nowa": "Zacznij od nowa",
        "wznow_naglowek": "Masz kod z jakiegoś etapu, a apka go nie zaliczyła? Wpisz go tutaj",
        "kod_label": "Kod:",
        "wznow_btn": "Zatwierdź kod",
        "wznow_ok": "Zaliczone!",
        "nie_rozpoznaje": "Nie rozpoznaję tego kodu.",
        "kod_do_sejfu": "Kod do sejfu:",
        "ukonczone_w": "Ukończone w",
        "min": "min",
    },
    "en": {
        "rozpocznij": "Start 🔓",
        "wroc_do_menu": "⬅ Back to menu",
        "sprawdz": "Check",
        "zatwierdz": "Confirm (one attempt!)",
        "twoja_odpowiedz": "Your answer:",
        "wybierz": "— choose —",
        "zle_sprobuj": "Not quite. Try again.",
        "zle_jedna_proba": "Wrong date. This puzzle is now locked — you only got one attempt.",
        "wybierz_date": "Pick a date:",
        "jedna_proba_info": "⚠️ You only get ONE attempt — choose carefully.",
        "wybierz_najpierw": "Pick a date first.",
        "poprawnych": "Correct",
        "twoj_ruch": "Your move:",
        "format_ruchu": "Type your move as start-square + end-square, e.g. `e2e4`.",
        "kod_z_gry_info": "When you beat all 3 levels, type the code from the game below:",
        "kod_z_gry_label": "Code from the game:",
        "zle_kod_gry": "That's not the code. Play again and check carefully!",
        "rozwiazane_status": "✅ Solved",
        "zamkniete_status": "🔒 Locked (wrong attempt — your one shot is used)",
        "menu_tytul": "Choose a stage",
        "wszystko_rozwiazane": "🎉 You solved everything!",
        "zobacz_kod": "See the safe code 🔓",
        "przegrana_tytul": "Game over",
        "przegrana_wiadomosc": "Nice try, go practice 😏\n\nThe hangman is complete — everything starts over.",
        "zacznij_od_nowa": "Start over",
        "wznow_naglowek": "Got a code from some stage that didn't register? Enter it here",
        "kod_label": "Code:",
        "wznow_btn": "Submit code",
        "wznow_ok": "Registered!",
        "nie_rozpoznaje": "I don't recognize that code.",
        "kod_do_sejfu": "Safe code:",
        "ukonczone_w": "Completed in",
        "min": "min",
    },
}


def t(klucz):
    jezyk = st.session_state.get("jezyk", "pl")
    return TEKST.get(jezyk, TEKST["pl"]).get(klucz, klucz)


def tt(dwujezyczny):
    """Zwraca wersję PL/EN danego tekstu jeśli to słownik {"pl":..,"en":..};
    zwykły string (np. celowo nietłumaczona zagadka 'po ptakach') zwraca wprost."""
    if isinstance(dwujezyczny, dict):
        jezyk = st.session_state.get("jezyk", "pl")
        return dwujezyczny.get(jezyk, dwujezyczny.get("pl", ""))
    return dwujezyczny


# ======================================================================
# SZABLON MINI-GRY (HTML/CSS/JS) — nie musisz tu nic zmieniać.
# Trudność steruje się z góry pliku, przez POZIOMY_GRY. Uwaga: teksty
# wewnątrz tej mini-gry są na razie tylko po polsku.
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
    align-items: center;
    padding: 10px 16px;
    color: #f5f5f0;
    font-size: 15px;
    font-weight: 600;
  }
  .wycisz-btn {
    background: none;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 20px;
    color: #f5f5f0;
    font-size: 16px;
    padding: 2px 10px;
    cursor: pointer;
  }
  #gra {
    position: relative;
    width: 100%;
    height: 420px;
    overflow: hidden;
    border-radius: 16px;
    border: 2px solid #d4af37;
  }
  .item {
    position: absolute;
    font-size: 34px;
    line-height: 1;
    cursor: pointer;
    transition: transform 0.15s ease, opacity 0.15s ease, filter 0.2s ease;
  }
  .item.zlapane {
    transform: scale(1.7);
    opacity: 0;
  }
  .item.zlapane-zle {
    transform: scale(1.4);
    filter: brightness(3) drop-shadow(0 0 14px #ff3b3b);
  }
  #nakladka {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(13,13,13,0.95);
    color: #e6c15c;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 24px;
  }
  #nakladka h2 { font-size: 22px; margin: 0 0 8px; }
  #nakladka p { margin: 0 0 6px; font-size: 14px; opacity: 0.85; }
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
    padding: 10px 26px;
    border-radius: 30px;
    font-weight: 700;
    color: #1a1a1a;
    cursor: pointer;
    font-size: 15px;
    margin-top: 10px;
  }
</style>
</head>
<body>
  <div id="panel">
    <span id="poziomEtykieta">Poziom 1</span>
    <button class="wycisz-btn" id="wyciszBtn">🔊</button>
  </div>
  <div id="gra">
    <div id="nakladka">
      <h2 id="nakladkaTytul">Poziom 1</h2>
      <p id="nakladkaOpis">Łap kolorowe serca. Omijaj czarne — jedna pomyłka i zaczynasz poziom od nowa.</p>
      <div id="kodBox" style="display:none;">
        <div id="kodWygrany">__KOD_GRY__</div>
        <p style="opacity:0.7; font-size:13px;">Przepisz ten kod poniżej 👇</p>
      </div>
      <button class="gra-btn" id="nakladkaBtn">Graj ▶</button>
    </div>
  </div>

<script>
  var POZIOMY = __POZIOMY_JSON__;
  var KOLORY = ['❤️','💛','💚','💙','💜','🧡'];

  var gra = document.getElementById('gra');
  var nakladka = document.getElementById('nakladka');
  var nakladkaTytul = document.getElementById('nakladkaTytul');
  var nakladkaOpis = document.getElementById('nakladkaOpis');
  var nakladkaBtn = document.getElementById('nakladkaBtn');
  var kodBox = document.getElementById('kodBox');
  var poziomEtykieta = document.getElementById('poziomEtykieta');
  var wyciszBtn = document.getElementById('wyciszBtn');

  var aktualnyPoziom = 0;
  var poziom = null;
  var kolejka = [];
  var doZlapania = 0;
  var aktywneElementy = [];
  var interwalSpawn = null;
  var trwa = false;
  var ostatniCzas = null;
  var wyciszone = false;

  var audioCtx = null;
  var bipInterval = null;

  function losowo(min, max) { return Math.random() * (max - min) + min; }

  function inicjujDzwiek() {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
    } catch (e) {
      audioCtx = null;
    }
  }

  function zagrajBip(czestotliwosc) {
    if (!audioCtx || wyciszone) return;
    try {
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.value = czestotliwosc;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.16, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.16);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.16);
    } catch (e) {
      // dźwięk to dodatek — jego brak nie może zepsuć gry
    }
  }

  function startMuzyka(tempoMs) {
    zatrzymajMuzyke();
    var nuty = [220, 220, 277, 220];
    var i = 0;
    bipInterval = setInterval(function () {
      zagrajBip(nuty[i % nuty.length]);
      i++;
    }, tempoMs);
  }

  function zatrzymajMuzyke() {
    if (bipInterval) {
      clearInterval(bipInterval);
      bipInterval = null;
    }
  }

  function stworzElement(zly) {
    var el = document.createElement('div');
    el.className = 'item';
    el.textContent = zly ? '🖤' : KOLORY[Math.floor(Math.random() * KOLORY.length)];
    el.dataset.zly = zly ? '1' : '0';

    var szer = gra.clientWidth;
    var wys = gra.clientHeight;
    var predkosc = poziom.predkosc;
    var x, y, vx, vy;

    if (poziom.kierunek === 'gora') {
      x = szer + 30;
      y = wys + 30;
      vx = -predkosc * 0.85;
      vy = -predkosc;
    } else if (poziom.kierunek === 'skos') {
      x = losowo(10, szer - 40);
      y = -40;
      vx = losowo(-90, 90);
      vy = predkosc;
    } else {
      x = losowo(10, szer - 40);
      y = -40;
      vx = losowo(-25, 25);
      vy = predkosc;
    }

    el.style.left = x + 'px';
    el.style.top = y + 'px';
    el.dataset.x = x;
    el.dataset.y = y;
    el.dataset.vx = vx;
    el.dataset.vy = vy;

    el.addEventListener('click', function () { kliknieto(el); });
    el.addEventListener('touchstart', function (e) { e.preventDefault(); kliknieto(el); }, { passive: false });

    gra.appendChild(el);
    aktywneElementy.push(el);
  }

  function kliknieto(el) {
    if (!trwa || el.dataset.klik) return;
    el.dataset.klik = '1';
    var zly = el.dataset.zly === '1';

    if (zly) {
      el.classList.add('zlapane-zle');
      trwa = false;
      clearInterval(interwalSpawn);
      setTimeout(function () { zakonczPoziom(false, 'czarne'); }, 220);
    } else {
      el.classList.add('zlapane');
      setTimeout(function () { usunElement(el); }, 150);
      doZlapania -= 1;
      if (doZlapania <= 0) {
        trwa = false;
        clearInterval(interwalSpawn);
        setTimeout(function () { zakonczPoziom(true); }, 200);
      }
    }
  }

  function usunElement(el) {
    var idx = aktywneElementy.indexOf(el);
    if (idx > -1) aktywneElementy.splice(idx, 1);
    if (el.parentNode) el.remove();
  }

  function petlaAnimacji(czas) {
    if (!trwa) { ostatniCzas = null; return; }
    if (ostatniCzas === null) ostatniCzas = czas;
    var dt = (czas - ostatniCzas) / 1000;
    ostatniCzas = czas;

    var szer = gra.clientWidth;
    var wys = gra.clientHeight;

    for (var i = aktywneElementy.length - 1; i >= 0; i--) {
      var el = aktywneElementy[i];
      var x = parseFloat(el.dataset.x) + parseFloat(el.dataset.vx) * dt;
      var y = parseFloat(el.dataset.y) + parseFloat(el.dataset.vy) * dt;
      el.dataset.x = x;
      el.dataset.y = y;
      el.style.left = x + 'px';
      el.style.top = y + 'px';

      if (y < -60 || y > wys + 60 || x < -60 || x > szer + 60) {
        var bylZly = el.dataset.zly === '1';
        var zlapany = el.dataset.klik === '1';
        usunElement(el);
        if (!zlapany && !bylZly && trwa) {
          trwa = false;
          clearInterval(interwalSpawn);
          zakonczPoziom(false, 'ucieklo');
          return;
        }
      }
    }

    requestAnimationFrame(petlaAnimacji);
  }

  function startPoziom(indeks) {
    aktualnyPoziom = indeks;
    poziom = POZIOMY[indeks];
    poziomEtykieta.textContent = 'Poziom ' + (indeks + 1);

    var lista = [];
    var i;
    for (i = 0; i < poziom.serca; i++) lista.push(false);
    for (i = 0; i < poziom.czarne; i++) lista.push(true);
    for (i = lista.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = lista[i]; lista[i] = lista[j]; lista[j] = tmp;
    }
    kolejka = lista;
    doZlapania = poziom.serca;

    aktywneElementy.forEach(function (el) { el.remove(); });
    aktywneElementy = [];

    nakladka.style.display = 'none';
    trwa = true;
    ostatniCzas = null;

    interwalSpawn = setInterval(function () {
      if (kolejka.length === 0) { clearInterval(interwalSpawn); return; }
      stworzElement(kolejka.shift());
    }, poziom.tempo);

    requestAnimationFrame(petlaAnimacji);

    if (!wyciszone) {
      inicjujDzwiek();
      startMuzyka(poziom.tempo);
    }
  }

  function opisPoziomu(indeks) {
    if (indeks === 1) return 'Poziom 2 — szybciej i na ukos.';
    if (indeks === 2) return 'Poziom 3 — najszybciej, pod górę, od prawej do lewej.';
    return '';
  }

  function zakonczPoziom(wygrana, powod) {
    zatrzymajMuzyke();
    aktywneElementy.forEach(function (el) { el.remove(); });
    aktywneElementy = [];
    nakladka.style.display = 'flex';

    if (wygrana) {
      if (aktualnyPoziom >= POZIOMY.length - 1) {
        nakladkaTytul.textContent = '🎉 Wygrałaś!';
        nakladkaOpis.textContent = 'Twój kod czeka poniżej:';
        kodBox.style.display = 'block';
        nakladkaBtn.style.display = 'none';
      } else {
        var nastepny = aktualnyPoziom + 1;
        nakladkaTytul.textContent = '🎉 Poziom ' + (aktualnyPoziom + 1) + ' ukończony!';
        nakladkaOpis.textContent = opisPoziomu(nastepny);
        kodBox.style.display = 'none';
        nakladkaBtn.style.display = 'inline-block';
        nakladkaBtn.textContent = 'Graj ▶';
        nakladkaBtn.onclick = function () { inicjujDzwiek(); startPoziom(nastepny); };
      }
    } else {
      nakladkaTytul.textContent = powod === 'czarne' ? '🖤 To było czarne serce...' : '💔 Serduszko uciekło...';
      nakladkaOpis.textContent = 'Trzeba złapać wszystkie, bez pomyłek. Spróbuj ponownie.';
      kodBox.style.display = 'none';
      nakladkaBtn.style.display = 'inline-block';
      nakladkaBtn.textContent = 'Jeszcze raz';
      nakladkaBtn.onclick = function () { inicjujDzwiek(); startPoziom(aktualnyPoziom); };
    }
  }

  wyciszBtn.addEventListener('click', function () {
    wyciszone = !wyciszone;
    wyciszBtn.textContent = wyciszone ? '🔇' : '🔊';
    if (wyciszone) {
      zatrzymajMuzyke();
    } else if (trwa) {
      inicjujDzwiek();
      startMuzyka(poziom.tempo);
    }
  });

  nakladkaBtn.onclick = function () { inicjujDzwiek(); startPoziom(0); };
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
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4ade80, #22c55e) !important;
    color: #062e14 !important;
}
div.stButton > button:disabled {
    opacity: 0.45;
    background: #333 !important;
    color: #999 !important;
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
# WISIELEC — wspólny licznik pomyłek (10 elementów)
# ======================================================================

WISIELEC_CZESCI = [
    '<line x1="10" y1="140" x2="70" y2="140" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="30" y1="140" x2="30" y2="10" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="30" y1="10" x2="90" y2="10" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="10" x2="90" y2="25" stroke="#e6c15c" stroke-width="4" stroke-linecap="round"/>',
    '<circle cx="90" cy="36" r="11" stroke="#ff6b6b" stroke-width="4" fill="none"/>',
    '<line x1="90" y1="47" x2="90" y2="85" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="57" x2="70" y2="72" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="57" x2="110" y2="72" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="85" x2="75" y2="112" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
    '<line x1="90" y1="85" x2="105" y2="112" stroke="#ff6b6b" stroke-width="4" stroke-linecap="round"/>',
]


def rysuj_wisielca(liczba_bledow, mala=False):
    liczba_bledow = max(0, min(10, liczba_bledow))
    widoczne = "".join(WISIELEC_CZESCI[:liczba_bledow])
    rozmiar = 70 if mala else 120
    wysokosc = int(rozmiar * 150 / 120)
    st.markdown(
        f"<div style='text-align:center;'><svg width='{rozmiar}' height='{wysokosc}' "
        f"viewBox='0 0 120 150'>{widoczne}</svg></div>",
        unsafe_allow_html=True,
    )


def pokaz_szachownice(pozycja):
    kolumny = "abcdefgh"
    wiersze = "87654321"
    komorki = []
    for wiersz_znak in wiersze:
        rank_idx = int(wiersz_znak) - 1
        for kolumna in kolumny:
            file_idx = ord(kolumna) - ord("a")
            pole = kolumna + wiersz_znak
            ciemne = (file_idx + rank_idx) % 2 == 0
            tlo = "#7a5c3e" if ciemne else "#e8d9b5"
            figura = pozycja.get(pole, "")
            komorki.append(
                f"<div style='background:{tlo}; display:flex; align-items:center; "
                f"justify-content:center; font-size:1.6rem;'>{figura}</div>"
            )
    siatka = "".join(komorki)
    st.markdown(
        "<div style='display:grid; grid-template-columns:repeat(8,1fr); "
        "grid-template-rows:repeat(8,2.4rem); max-width:340px; margin:0.5rem auto; "
        f"border:2px solid #d4af37; border-radius:8px; overflow:hidden;'>{siatka}</div>",
        unsafe_allow_html=True,
    )


# ======================================================================
# TRWAŁY STAN — przetrwa zamknięcie telefonu i wznowienie po jakimś czasie.
# Zapisywany w DWÓCH miejscach naraz (link + plik na serwerze).
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
    st.query_params["r"] = ",".join(sorted(st.session_state.rozwiazane))
    st.query_params["n"] = ",".join(sorted(st.session_state.nieudane))
    st.query_params["b"] = str(st.session_state.bledy_wisielec)
    st.query_params["j"] = st.session_state.jezyk
    if st.session_state.czas_startu:
        st.query_params["t"] = str(st.session_state.czas_startu)
    dane = {
        "rozwiazane": list(st.session_state.rozwiazane),
        "nieudane": list(st.session_state.nieudane),
        "bledy_wisielec": st.session_state.bledy_wisielec,
        "jezyk": st.session_state.jezyk,
        "czas_startu": st.session_state.czas_startu,
    }
    try:
        with open(PLIK_STANU, "w", encoding="utf-8") as f:
            json.dump(dane, f)
    except Exception:
        pass


def zainicjuj_stan():
    if "rozwiazane" in st.session_state:
        return

    r = st.query_params.get("r", "")
    rozwiazane_url = set(x for x in r.split(",") if x)
    n = st.query_params.get("n", "")
    nieudane_url = set(x for x in n.split(",") if x)
    b = st.query_params.get("b")
    bledy_url = int(b) if b and b.isdigit() else 0
    j = st.query_params.get("j")
    jezyk_url = j if j in ("pl", "en") else None
    t_param = st.query_params.get("t")
    czas_url = float(t_param) if t_param else None

    zapisane = wczytaj_zapisany_stan() or {}
    rozwiazane_plik = set(zapisane.get("rozwiazane", []))
    nieudane_plik = set(zapisane.get("nieudane", []))
    bledy_plik = zapisane.get("bledy_wisielec", 0)
    jezyk_plik = zapisane.get("jezyk")
    czas_plik = zapisane.get("czas_startu")

    st.session_state.rozwiazane = rozwiazane_url | rozwiazane_plik
    st.session_state.nieudane = nieudane_url | nieudane_plik
    st.session_state.bledy_wisielec = max(bledy_url, bledy_plik)
    st.session_state.jezyk = jezyk_url or jezyk_plik or "pl"
    st.session_state.czas_startu = czas_url or czas_plik

    juz_zaczela = bool(
        jezyk_url or jezyk_plik
        or st.session_state.rozwiazane or st.session_state.nieudane
        or st.session_state.bledy_wisielec
    )
    st.session_state.ekran = "menu" if juz_zaczela else "powitanie"

    if juz_zaczela:
        zapisz_postep()


def wznow_z_kodu(kod):
    kod = kod.strip().lower()
    if not kod:
        return False
    for etap_dane in ETAPY:
        oczekiwana = str(etap_dane.get("odpowiedz", "")).strip().lower()
        if oczekiwana and oczekiwana == kod:
            st.session_state.rozwiazane.add(etap_dane["klucz"])
            zapisz_postep()
            return True
    return False


# ======================================================================
# RENDEROWANIE POJEDYNCZYCH TYPÓW ZAGADEK
# Każdy zwraca: True (poprawnie), False (źle — dopiero co wysłane), albo
# None (nic jeszcze nie wysłano w tym przebiegu).
# ======================================================================

def renderuj_haslo(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))
    wpisane = st.text_input(t("twoja_odpowiedz"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


def renderuj_quiz(etap_dane):
    klucz = etap_dane["klucz"]
    placeholder = t("wybierz")
    odpowiedzi = []
    for idx, pytanie in enumerate(etap_dane["pytania"]):
        wybor = st.radio(
            tt(pytanie["pytanie"]),
            [placeholder] + [tt(o) for o in pytanie["opcje"]],
            key=f"{klucz}_pyt_{idx}",
        )
        odpowiedzi.append(wybor)

    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        poprawne = 0
        for idx, pytanie in enumerate(etap_dane["pytania"]):
            oczekiwana = tt(pytanie["opcje"][pytanie["poprawna"]])
            if odpowiedzi[idx] == oczekiwana:
                poprawne += 1
        procent = poprawne / len(etap_dane["pytania"])
        if procent >= etap_dane.get("prog", 1.0):
            return True
        st.warning(f"{t('poprawnych')}: {poprawne}/{len(etap_dane['pytania'])}.")
        return False
    return None


def renderuj_gra(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane.get("opis", "")))

    html = (
        SZABLON_GRY
        .replace("__POZIOMY_JSON__", json.dumps(POZIOMY_GRY))
        .replace("__KOD_GRY__", str(KOD_GRY))
    )
    components.html(html, height=520, scrolling=False)

    st.caption(t("kod_z_gry_info"))
    wpisane = st.text_input(t("kod_z_gry_label"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        if wpisane.strip().lower() == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error(t("zle_kod_gry"))
        return False
    return None


def renderuj_data(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))
    st.caption(t("jedna_proba_info"))
    wybrana = st.date_input(t("wybierz_date"), key=f"data_{klucz}", value=None, format="DD.MM.YYYY")
    if st.button(t("zatwierdz"), key=f"btn_{klucz}"):
        if wybrana is None:
            st.warning(t("wybierz_najpierw"))
            return None
        if wybrana == etap_dane["data"]:
            return True
        st.error(t("zle_jedna_proba"))
        return False
    return None


def renderuj_szachy(etap_dane):
    klucz = etap_dane["klucz"]
    st.markdown(tt(etap_dane["tresc"]))
    pokaz_szachownice(etap_dane["pozycja"])
    st.caption(t("format_ruchu"))
    wpisane = st.text_input(t("twoj_ruch"), key=f"pole_{klucz}")
    if st.button(t("sprawdz"), key=f"btn_{klucz}"):
        czyste = wpisane.strip().lower().replace(" ", "")
        if czyste == str(etap_dane["odpowiedz"]).strip().lower():
            return True
        st.error(t("zle_sprobuj"))
        return False
    return None


# ======================================================================
# EKRANY
# ======================================================================

def pokaz_powitanie():
    st.markdown("<div class='zamek-ikona'>🔒</div>", unsafe_allow_html=True)

    kolumny = st.columns(2)
    with kolumny[0]:
        if st.button("🇵🇱 Polski", key="jezyk_pl"):
            st.session_state.jezyk = "pl"
            st.rerun()
    with kolumny[1]:
        if st.button("🇬🇧 English", key="jezyk_en"):
            st.session_state.jezyk = "en"
            st.rerun()

    st.markdown(f"<h1 class='tytul'>{tt(POWITANIE_TYTUL)}</h1>", unsafe_allow_html=True)
    st.markdown(tt(WIADOMOSC_POWITALNA))

    if st.button(t("rozpocznij"), key="start_btn"):
        st.session_state.ekran = "menu"
        st.session_state.czas_startu = time.time()
        zapisz_postep()
        st.rerun()

    with st.expander(t("wznow_naglowek")):
        kod_wznow = st.text_input(t("kod_label"), key="wznow_input")
        if st.button(t("wznow_btn"), key="wznow_btn2"):
            if wznow_z_kodu(kod_wznow):
                st.success(t("wznow_ok"))
            else:
                st.error(t("nie_rozpoznaje"))


def pokaz_menu():
    st.markdown(f"<h1 class='tytul'>{t('menu_tytul')}</h1>", unsafe_allow_html=True)
    rysuj_wisielca(st.session_state.bledy_wisielec)

    kolumny = st.columns(2)
    for i, etap_dane in enumerate(ETAPY):
        klucz = etap_dane["klucz"]
        rozwiazany = klucz in st.session_state.rozwiazane
        nieudany = klucz in st.session_state.nieudane
        prefiks = "✅ " if rozwiazany else ("🔒 " if nieudany else "")
        etykieta = prefiks + tt(etap_dane["tytul"])
        with kolumny[i % 2]:
            if st.button(
                etykieta,
                key=f"menu_{klucz}",
                type="primary" if rozwiazany else "secondary",
                disabled=nieudany,
            ):
                st.session_state.ekran = f"etap:{klucz}"
                st.rerun()

    wszystkie = all(e["klucz"] in st.session_state.rozwiazane for e in ETAPY)
    if wszystkie:
        st.success(t("wszystko_rozwiazane"))
        if st.button(t("zobacz_kod"), key="zobacz_kod_btn"):
            st.session_state.ekran = "final"
            st.rerun()

    with st.expander(t("wznow_naglowek")):
        kod_wznow = st.text_input(t("kod_label"), key="wznow_input_menu")
        if st.button(t("wznow_btn"), key="wznow_btn_menu"):
            if wznow_z_kodu(kod_wznow):
                st.success(t("wznow_ok"))
                st.rerun()
            else:
                st.error(t("nie_rozpoznaje"))


def pokaz_ekran_etapu(etap_dane):
    klucz = etap_dane["klucz"]

    if st.button(t("wroc_do_menu"), key=f"powrot_{klucz}"):
        st.session_state.ekran = "menu"
        st.rerun()

    rysuj_wisielca(st.session_state.bledy_wisielec, mala=True)
    st.markdown(f"<h2 class='tytul' style='font-size:1.5rem;'>{tt(etap_dane['tytul'])}</h2>", unsafe_allow_html=True)

    if klucz in st.session_state.rozwiazane:
        st.success(t("rozwiazane_status"))
        return
    if klucz in st.session_state.nieudane:
        st.error(t("zamkniete_status"))
        return

    typ = etap_dane["typ"]
    if typ == "haslo":
        wynik = renderuj_haslo(etap_dane)
    elif typ == "quiz":
        wynik = renderuj_quiz(etap_dane)
    elif typ == "gra":
        wynik = renderuj_gra(etap_dane)
    elif typ == "data":
        wynik = renderuj_data(etap_dane)
    elif typ == "szachy":
        wynik = renderuj_szachy(etap_dane)
    else:
        wynik = None

    if wynik is True:
        st.session_state.rozwiazane.add(klucz)
        zapisz_postep()
        st.balloons()
        st.rerun()
    elif wynik is False:
        st.session_state.bledy_wisielec += 1
        if etap_dane.get("jedna_proba"):
            st.session_state.nieudane.add(klucz)
        zapisz_postep()
        if st.session_state.bledy_wisielec >= 10:
            st.session_state.ekran = "przegrana"
            st.rerun()


def pokaz_final():
    st.balloons()
    st.markdown("<div class='zamek-otwarty'>🔓</div>", unsafe_allow_html=True)
    st.markdown(f"<h1 class='tytul'>{t('wszystko_rozwiazane')}</h1>", unsafe_allow_html=True)
    st.markdown(tt(WIADOMOSC_KONCOWA))

    kod_koncowy = "".join(str(e["cyfra"]) for e in ETAPY)
    tarcze = "".join(f"<div class='cyfra-tarcza'>{c}</div>" for c in kod_koncowy)
    st.markdown(
        f"""
        <div style='text-align:center; margin-top:1.5rem;'>
          <div style='font-size:0.95rem; opacity:0.75; margin-bottom:0.6rem;'>{t('kod_do_sejfu')}</div>
          <div style='display:flex; justify-content:center; gap:0.5rem;'>{tarcze}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.czas_startu:
        minuty = (time.time() - st.session_state.czas_startu) / 60
        st.caption(f"⏱️ {t('ukonczone_w')} {minuty:.1f} {t('min')}")

    if st.button(t("wroc_do_menu"), key="powrot_final"):
        st.session_state.ekran = "menu"
        st.rerun()


def pokaz_przegrana():
    rysuj_wisielca(10)
    st.markdown(f"<h1 class='tytul'>{t('przegrana_tytul')}</h1>", unsafe_allow_html=True)
    st.markdown(t("przegrana_wiadomosc"))
    if st.button(t("zacznij_od_nowa"), key="restart_btn"):
        jezyk = st.session_state.jezyk
        st.session_state.rozwiazane = set()
        st.session_state.nieudane = set()
        st.session_state.bledy_wisielec = 0
        st.session_state.czas_startu = None
        st.session_state.jezyk = jezyk
        st.session_state.ekran = "menu"
        zapisz_postep()
        st.rerun()


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

    ekran = st.session_state.ekran

    if ekran == "powitanie":
        pokaz_powitanie()
    elif ekran == "przegrana":
        pokaz_przegrana()
    elif ekran == "final":
        pokaz_final()
    elif ekran.startswith("etap:"):
        klucz = ekran.split(":", 1)[1]
        etap_dane = next((e for e in ETAPY if e["klucz"] == klucz), None)
        if etap_dane is None:
            st.session_state.ekran = "menu"
            st.rerun()
        else:
            pokaz_ekran_etapu(etap_dane)
    else:
        pokaz_menu()


if __name__ == "__main__":
    main()
