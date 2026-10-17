"""
SmartHazri v3 - Attendance App (Kivy, single file)

Pydroid 3: Menu -> Pip -> "kivy" install karo, phir ye file kholo aur Play dabao.
(Photo chhoti karne ke liye Pillow ho to achha hai, na ho tab bhi chalega.)
APK: isi file ko main.py naam se Buildozer me use karo.

NOTE: v2 ka data (smarthazri2.db) isme bhi chalega, kuch delete nahi hoga.
"""
import os, csv, time, shutil, sqlite3, hashlib, calendar, datetime as dt
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import get_color_from_hex as hx
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

WHITE = [1, 1, 1, 1]
BG, AC, OK, NO, LV = hx("#f4f5fb"), hx("#4f46e5"), hx("#16a34a"), hx("#dc2626"), hx("#d97706")
MU, TX, GR = hx("#6b7280"), hx("#161a26"), hx("#e5e7eb")
ST_COL = {"P": OK, "A": NO, "L": LV}
ST_TXT = {"P": "Present", "A": "Absent", "L": "Leave"}
BRANCHES = ["CSE", "IT", "AI", "AIML", "DS", "ECE", "EE", "ME", "CE", "Other"]
YEARS = ["1st", "2nd", "3rd", "4th"]
SECS = ["A", "B", "C", "D", "E", "F"]
BATCHES = ["B1", "B2", "B3", "B4"]
CLASSES = ["Nursery", "LKG", "UKG"] + [str(i) for i in range(1, 13)]
SSECS = ["-", "A", "B", "C", "D", "E"]
NONE_T = "(koi nahi)"

KV = """
<Panel>:
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(self.rad)]
<RBtn>:
    canvas.before:
        Color:
            rgba: self.bg if self.state == 'normal' else [self.bg[0]*.78, self.bg[1]*.78, self.bg[2]*.78, 1]
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
<Cell>:
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]
<Bar>:
    canvas:
        Color:
            rgba: .9, .91, .94, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(5)]
        Color:
            rgba: self.col
        RoundedRectangle:
            pos: self.pos
            size: self.width * min(max(self.value, 0), 100) / 100., self.height
            radius: [dp(5)]
<Ring>:
    canvas:
        Color:
            rgba: .9, .91, .94, 1
        Line:
            circle: (self.center_x, self.center_y, dp(52))
            width: dp(9)
        Color:
            rgba: self.col
        Line:
            circle: (self.center_x, self.center_y, dp(52), 0, max(0.5, self.value * 3.6))
            width: dp(9)
            cap: 'round'
    Label:
        text: '%d%%' % root.value
        font_size: sp(26)
        bold: True
        color: .09, .1, .15, 1
<Initials>:
    canvas.before:
        Color:
            rgba: .49, .23, .93, 1
        Ellipse:
            pos: self.pos
            size: self.size
    Label:
        text: root.text
        font_size: sp(26)
        bold: True
        color: 1, 1, 1, 1
"""


# ---------- widgets & helpers ----------
class Panel(BoxLayout):
    bg = ListProperty(WHITE)
    rad = NumericProperty(16)


class Card(Panel):
    def __init__(self, **k):
        k.setdefault("orientation", "vertical")
        k.setdefault("padding", dp(14))
        k.setdefault("spacing", dp(6))
        super().__init__(size_hint_y=None, **k)
        self.bind(minimum_height=self.setter("height"))


class RBtn(ButtonBehavior, Label):
    bg = ListProperty(AC)

    def __init__(self, **k):
        k.setdefault("size_hint_y", None)
        k.setdefault("height", dp(46))
        k.setdefault("bold", True)
        k.setdefault("font_size", sp(14))
        super().__init__(**k)


class Cell(Label):
    bg = ListProperty(GR)


class DayCell(ButtonBehavior, Cell):
    pass


class Bar(Widget):
    value = NumericProperty(0)
    col = ListProperty(OK)


class Ring(FloatLayout):
    value = NumericProperty(0)
    col = ListProperty(OK)


class Initials(FloatLayout):
    text = StringProperty("")


def lbl(t, size=14, color=TX, bold=False, align="left", w=None):
    l = Label(text=str(t), font_size=sp(size), color=color, bold=bold, halign=align, valign="middle", size_hint_y=None)
    if w:
        l.size_hint_x = None
        l.width = dp(w)
    l.bind(width=lambda i, v: setattr(i, "text_size", (v, None)))
    l.bind(texture_size=lambda i, s: setattr(i, "height", s[1] + dp(6)))
    return l


def inp(hint, text="", password=False):
    return TextInput(hint_text=hint, text=text, multiline=False, password=password, size_hint_y=None, height=dp(46),
                     padding=[dp(12), dp(13)], font_size=sp(15), write_tab=False, background_normal="", background_active="",
                     background_color=[.96, .96, .98, 1], foreground_color=TX, cursor_color=AC)


def tin(st, key, hint, password=False, num=False):
    t = inp(hint, st.get(key, ""), password)
    if num:
        t.input_filter = "int"
    t.bind(text=lambda i, v: st.__setitem__(key, v))
    return t


def spin(st, key, values, cb=None):
    s = Spinner(text=st.get(key) if st.get(key) in values else values[0], values=values, size_hint_y=None, height=dp(46),
                font_size=sp(15), background_normal="", background_color=[.96, .96, .98, 1], color=TX)
    st[key] = s.text
    s.bind(text=lambda i, v: (st.__setitem__(key, v), cb and Clock.schedule_once(lambda d: cb(), 0)))
    return s


def row(*ws, h=46, gap=8):
    r = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(h), spacing=dp(gap))
    for w in ws:
        r.add_widget(w)
    return r


def small(text, cb, bg=MU, w=48):
    return RBtn(text=text, bg=bg, size_hint_x=None, width=dp(w), on_release=lambda *_: cb())


def msg(title, text):
    b = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    b.add_widget(lbl(text, 14))
    p = Popup(title=title, content=b, size_hint=(.9, None), height=dp(230))
    b.add_widget(RBtn(text="OK", on_release=lambda *_: p.dismiss()))
    p.open()


def ask(title, text, yes):
    b = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    b.add_widget(lbl(text, 14))
    p = Popup(title=title, content=b, size_hint=(.9, None), height=dp(230))
    b.add_widget(row(RBtn(text="Cancel", bg=MU, on_release=lambda *_: p.dismiss()),
                     RBtn(text="Yes", bg=NO, on_release=lambda *_: (p.dismiss(), yes()))))
    p.open()


def prompt(title, hint, done, password=True):
    b = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    t = inp(hint, password=password)
    b.add_widget(t)
    p = Popup(title=title, content=b, size_hint=(.9, None), height=dp(220))
    b.add_widget(row(RBtn(text="Cancel", bg=MU, on_release=lambda *_: p.dismiss()),
                     RBtn(text="OK", on_release=lambda *_: (p.dismiss(), done(t.text)))))
    p.open()


def info(title, text):
    b = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    sv = ScrollView()
    sv.add_widget(lbl(text, 14))
    b.add_widget(sv)
    p = Popup(title=title, content=b, size_hint=(.93, .72))
    b.add_widget(RBtn(text="Band karo", on_release=lambda *_: p.dismiss()))
    p.open()


def fld(c, st, label, key, **k):
    c.add_widget(lbl(label, 12, MU))
    c.add_widget(tin(st, key, label, **k))


def reg_state():
    return dict(new_state(), role="student", photo_src="", username="", pw="", pw2="", name="", surname="", mobile="",
                subject="", dept="", empid="", roll="", mentor_t=NONE_T, batch="B1")


def grow(bar, val, delay=.25):
    Clock.schedule_once(lambda d: Animation(value=val, d=.9, t="out_cubic").start(bar), delay)


def hp(pw, salt=None):
    salt = salt or os.urandom(8).hex()
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 60000).hex()


def chk(pw, stored):
    return hp(pw, stored.split("$")[0]) == stored


def today():
    return dt.date.today().isoformat()


def vd(x):
    try:
        dt.date.fromisoformat(x)
        return True
    except Exception:
        return False


def fullname(u):
    return ("%s %s" % (u["name"], u["surname"])).strip()


def bval(d):
    return d["branch_o"].strip().upper() if d.get("branch") == "Other" else d["branch"]


def glabel(d):
    if d["inst"] == "college":
        s = "%s | %s Year | Sec %s" % (bval(d), d["year"], d["sec"])
        return s + ("" if d["batch"] == "All" else " | " + d["batch"])
    s = "Class %s" % d["cls"]
    return s + (" | All sections" if d["sec"] == "All" else "" if d["sec"] == "-" else " | Sec " + d["sec"])


def gwhere(d):
    if d["inst"] == "college":
        w, a = "inst='college' AND branch=? AND year=? AND sec=?", [bval(d), d["year"], d["sec"]]
        if d["batch"] != "All":
            w += " AND batch=?"
            a.append(d["batch"])
    else:
        w, a = "inst='school' AND cls=?", [d["cls"]]
        if d["sec"] != "All":
            w += " AND sec=?"
            a.append(d["sec"])
    return w, a


def class_fields(st, sel, rebuild):
    """College: branch/year/section/batch. School: class/section. sel=True => teacher ke liye 'All' option."""
    ws = []

    def add(label, key, values, cb=None):
        ws.append(lbl(label, 12, MU))
        ws.append(spin(st, key, values, cb))

    if st["inst"] == "college":
        add("Branch", "branch", BRANCHES, rebuild)
        if st["branch"] == "Other":
            ws.append(tin(st, "branch_o", "Apni branch likho (jaise CIVIL)"))
        add("Year", "year", YEARS)
        add("Section", "sec", SECS)
        add("Batch", "batch", (["All"] if sel else []) + BATCHES)
    else:
        add("Class", "cls", CLASSES)
        add("Section", "sec", (["All"] if sel else []) + SSECS)
    return ws


def avatar(u, size=80):
    ph = u.get("photo") or ""
    if ph and os.path.exists(ph):
        return Image(source=ph, size_hint=(None, None), size=(dp(size), dp(size)), pos_hint={"center_y": .5})
    ini = ((u.get("name") or "?")[:1] + (u.get("surname") or "")[:1]).upper()
    return Initials(text=ini, size_hint=(None, None), size=(dp(size), dp(size)), pos_hint={"center_y": .5})


def new_state():
    return dict(inst="college", branch="CSE", branch_o="", year="1st", sec="A", batch="All", cls="1")


class SmartHazri(App):
    title = "SmartHazri"

    # ---------- setup ----------
    def build(self):
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"
        Builder.load_string(KV)
        calendar.setfirstweekday(calendar.SUNDAY)
        self.ph_dir = os.path.join(self.user_data_dir, "photos")
        self.con = sqlite3.connect(os.path.join(self.user_data_dir, "smarthazri2.db"))
        self.con.executescript("""
        CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,pw TEXT,role TEXT,name TEXT,surname TEXT,mobile TEXT,photo TEXT,
            subject TEXT,dept TEXT,empid TEXT,roll TEXT,inst TEXT,branch TEXT,year TEXT,sec TEXT,batch TEXT,cls TEXT,mentor TEXT);
        CREATE TABLE IF NOT EXISTS att(d TEXT,sid TEXT,tid TEXT,st TEXT,PRIMARY KEY(d,sid,tid));
        CREATE TABLE IF NOT EXISTS leaves(id INTEGER PRIMARY KEY AUTOINCREMENT,sid TEXT,tid TEXT,fd TEXT,td TEXT,reason TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT);
        """)
        self.me, self.tab, self.hz, self.rep = None, 0, False, False
        self.grp = new_state()
        self.ns = reg_state()
        t0 = dt.date.today()
        self.cm = (t0.year, t0.month)
        self.main = BoxLayout(orientation="vertical")
        s = self.db("SELECT v FROM kv WHERE k='session'")
        u = self.urow(s[0][0]) if s else None
        if u:
            self.me = u
            self.portal()
        else:
            self.login_screen()
        return self.main

    def db(self, sql, a=()):
        c = self.con.execute(sql, a)
        self.con.commit()
        return c.fetchall()

    def rows(self, sql, a=()):
        c = self.con.cursor()
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute(sql, a).fetchall()]

    def urow(self, u):
        r = self.rows("SELECT * FROM users WHERE lower(username)=lower(?)", (u,))
        return r[0] if r else None

    def stat(self, sid, tid=None):
        r = dict(self.db("SELECT st,COUNT(*) FROM att WHERE sid=?" + (" AND tid=?" if tid else "") + " GROUP BY st", (sid, tid) if tid else (sid,)))
        p, a, l = r.get("P", 0), r.get("A", 0), r.get("L", 0)
        t = p + a
        return p, a, l, t, (round(p * 100 / t) if t else 0)

    def students(self, d):
        w, a = gwhere(d)
        return self.rows("SELECT * FROM users WHERE role='student' AND " + w + " ORDER BY length(roll), roll, name", a)

    def pending(self):
        return self.db("SELECT COUNT(*) FROM leaves WHERE (tid=? OR tid='') AND status='pending'", (self.me["username"],))[0][0]

    # ---------- page scaffolding ----------
    def new_page(self):
        sv = ScrollView(bar_width=dp(3))
        g = GridLayout(cols=1, size_hint_y=None, spacing=dp(10), padding=[dp(12), dp(10), dp(12), dp(16)])
        g.bind(minimum_height=g.setter("height"))
        sv.add_widget(g)
        return sv, g

    def fade(self, g):
        for i, w in enumerate(reversed(g.children)):
            w.opacity = 0
            Clock.schedule_once(lambda d, w=w: Animation(opacity=1, d=.4, t="out_quad").start(w), min(i, 10) * .06)

    def show(self, fn, anim=True):
        self.holder.clear_widgets()
        sv, g = self.new_page()
        fn(g)
        self.holder.add_widget(sv)
        if anim:
            self.fade(g)

    def refresh(self):
        self.show(self.tabs[self.tab][1], anim=False)

    # ---------- photo ----------
    def pick_photo(self, done):
        from kivy.uix.filechooser import FileChooserIconView
        start = "/storage/emulated/0" if os.path.isdir("/storage/emulated/0") else os.path.expanduser("~")
        fc = FileChooserIconView(path=start, filters=["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"])
        b = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6))
        b.add_widget(fc)
        p = Popup(title="Photo chuno", content=b, size_hint=(.96, .9))

        def ok(*_):
            if fc.selection:
                p.dismiss()
                done(fc.selection[0])
            else:
                msg("Dhyan do", "Pehle koi photo chuno.")

        b.add_widget(row(RBtn(text="Cancel", bg=MU, on_release=lambda *_: p.dismiss()), RBtn(text="Select", on_release=ok)))
        p.open()

    def save_photo(self, src, uname):
        try:
            os.makedirs(self.ph_dir, exist_ok=True)
            dst = os.path.join(self.ph_dir, "%s_%d.jpg" % (uname, int(time.time())))
            try:
                from PIL import Image as PI
                im = PI.open(src).convert("RGB")
                im.thumbnail((400, 400))
                im.save(dst, "JPEG", quality=85)
            except Exception:
                dst = dst[:-4] + (os.path.splitext(src)[1] or ".jpg")
                shutil.copy(src, dst)
            return dst
        except Exception:
            return ""

    # ---------- login / register ----------
    def enter(self, u):
        self.me, self.tab, self.hz, self.rep = u, 0, False, False
        self.db("INSERT OR REPLACE INTO kv VALUES('session',?)", (u["username"],))
        self.portal()

    def logout(self):
        def go():
            self.db("DELETE FROM kv WHERE k='session'")
            self.me = None
            self.login_screen()
        ask("Logout", "Logout karne par dobara username aur password dalna padega.", go)

    def login_screen(self):
        self.main.clear_widgets()
        sv, g = self.new_page()
        g.add_widget(lbl("SmartHazri", 34, AC, True, "center"))
        g.add_widget(lbl("Digital Attendance System", 14, MU, False, "center"))
        c = Card()
        u, p = inp("Username"), inp("Password", password=True)
        c.add_widget(u)
        c.add_widget(p)

        def go(*_):
            r = self.urow(u.text.strip())
            if not r or not chk(p.text, r["pw"]):
                return msg("Login fail", "Username ya password galat hai.")
            self.enter(r)

        c.add_widget(RBtn(text="Login", on_release=go))
        c.add_widget(RBtn(text="Naya account banao (Register)", bg=GR, color=AC, on_release=lambda *_: self.start_register()))
        c.add_widget(RBtn(text="Password bhool gaye?", bg=WHITE, color=MU, on_release=lambda *_: self.forgot()))
        g.add_widget(c)
        self.main.add_widget(sv)
        self.fade(g)

    def forgot(self):
        b = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        u, m, p = inp("Username"), inp("Registered mobile number"), inp("Naya password", password=True)
        for w in (u, m, p):
            b.add_widget(w)
        pop = Popup(title="Password reset", content=b, size_hint=(.92, None), height=dp(360))

        def go(*_):
            r = self.urow(u.text.strip())
            if not r or r["mobile"] != m.text.strip():
                return msg("Galat", "Username ya mobile number match nahi hua.")
            if len(p.text) < 4:
                return msg("Dhyan do", "Naya password kam se kam 4 akshar ka ho.")
            self.db("UPDATE users SET pw=? WHERE username=?", (hp(p.text), r["username"]))
            pop.dismiss()
            msg("Done", "Password badal gaya, ab login karo.")

        b.add_widget(RBtn(text="Password badlo", on_release=go))
        b.add_widget(RBtn(text="Cancel", bg=MU, on_release=lambda *_: pop.dismiss()))
        pop.open()

    def start_register(self):
        self.rg = reg_state()
        self.register_screen(True)

    def register_screen(self, anim=False):
        st = self.rg
        self.main.clear_widgets()
        sv, g = self.new_page()
        g.add_widget(lbl("Naya Account", 26, AC, True, "center"))
        c = Card()
        c.add_widget(lbl("Main kaun hu?", 12, MU))
        tb = {k: RBtn(text=t, bg=AC if st["role"] == k else GR, color=WHITE if st["role"] == k else MU,
                      on_release=lambda *_, k=k: (st.__setitem__("role", k), self.register_screen())) for k, t in (("student", "Student"), ("teacher", "Teacher"))}
        c.add_widget(row(tb["student"], tb["teacher"]))
        c.add_widget(row(avatar({"photo": st["photo_src"], "name": st["name"] or "?", "surname": st["surname"]}, 84),
                         RBtn(text="Profile photo chuno", bg=MU, pos_hint={"center_y": .5}, on_release=lambda *_: self.pick_photo(lambda p: (st.__setitem__("photo_src", p), self.register_screen()))), h=90))

        def f(label, key, hint="", **k):
            c.add_widget(lbl(label, 12, MU))
            c.add_widget(tin(st, key, hint or label, **k))

        f("Username (login ke liye)", "username")
        f("Password (4+ akshar)", "pw", password=True)
        f("Password dobara likho", "pw2", password=True)
        f("Naam (First name)", "name")
        f("Surname", "surname")
        f("Mobile number (10 digit)", "mobile", num=True)
        if st["role"] == "teacher":
            f("Kaun sa subject padhate ho?", "subject")
            f("Department", "dept")
            f("Employee ID (optional)", "empid")
        else:
            f("Roll number", "roll")
            c.add_widget(lbl("Padhai ka level", 12, MU))
            ib = {k: RBtn(text=t, bg=AC if st["inst"] == k else GR, color=WHITE if st["inst"] == k else MU,
                          on_release=lambda *_, k=k: (st.__setitem__("inst", k), self.register_screen())) for k, t in (("college", "College"), ("school", "School"))}
            c.add_widget(row(ib["college"], ib["school"]))
            for w in class_fields(st, False, self.register_screen):
                c.add_widget(w)
            tl = self.rows("SELECT username,name,surname,subject FROM users WHERE role='teacher' ORDER BY name")
            vals = [NONE_T] + ["%s %s - %s (%s)" % (t["name"], t["surname"], t["subject"], t["username"]) for t in tl]
            c.add_widget(lbl("Class teacher / Mentor (optional)", 12, MU))
            c.add_widget(spin(st, "mentor_t", vals))
        c.add_widget(RBtn(text="Register karo", on_release=lambda *_: self.do_register()))
        c.add_widget(RBtn(text="Wapas Login par", bg=MU, on_release=lambda *_: self.login_screen()))
        g.add_widget(c)
        self.main.add_widget(sv)
        if anim:
            self.fade(g)

    def do_register(self, st=None, add=False):
        st = st or self.rg
        u, t = st["username"].strip(), st["role"] == "teacher"
        if not u or not st["name"].strip() or not st["surname"].strip():
            return msg("Dhyan do", "Username, naam aur surname zaroori hain.")
        if len(u) < 3 or not all(ch.isalnum() or ch in "._" for ch in u):
            return msg("Dhyan do", "Username kam se kam 3 akshar ka ho (sirf letters, numbers, . aur _).")
        if len(st["pw"]) < 4 or st["pw"] != st["pw2"]:
            return msg("Dhyan do", "Password 4+ akshar ka ho aur dono baar same ho.")
        if not (st["mobile"].isdigit() and len(st["mobile"]) == 10):
            return msg("Dhyan do", "Mobile number 10 digit ka ho.")
        if self.urow(u):
            return msg("Dhyan do", "Ye username pehle se liya ja chuka hai.")
        if t and not st["subject"].strip():
            return msg("Dhyan do", "Subject likhna zaroori hai.")
        if not t:
            if not st["roll"].strip():
                return msg("Dhyan do", "Roll number likhna zaroori hai.")
            if st["inst"] == "college" and st["branch"] == "Other" and not st["branch_o"].strip():
                return msg("Dhyan do", "Apni branch ka naam likho.")
        col = st["inst"] == "college"
        d = dict(username=u, pw=hp(st["pw"]), role=st["role"], name=st["name"].strip(), surname=st["surname"].strip(), mobile=st["mobile"],
                 photo=self.save_photo(st["photo_src"], u) if st["photo_src"] else "",
                 subject=st["subject"].strip() if t else "", dept=st["dept"].strip() if t else "", empid=st["empid"].strip() if t else "",
                 roll="" if t else st["roll"].strip(), inst="" if t else st["inst"],
                 branch=bval(st) if (not t and col) else "", year=st["year"] if (not t and col) else "",
                 sec="" if t else st["sec"], batch=st["batch"] if (not t and col) else "", cls="" if (t or col) else st["cls"],
                 mentor="" if (t or st["mentor_t"] == NONE_T) else st["mentor_t"].rsplit("(", 1)[1].rstrip(")"))
        if add:
            d["mentor"] = self.me["username"]
        self.db("INSERT INTO users(%s) VALUES(%s)" % (",".join(d), ",".join(":" + k for k in d)), d)
        if add:
            return True
        self.enter(self.urow(u))

    # ---------- portal ----------
    def portal(self):
        self.main.clear_widgets()
        T = self.me["role"] == "teacher"
        self.tabs = ([("Home", self.t_home), ("Hazri", self.t_mark), ("Students", self.t_students), ("Report", self.t_report), ("Leaves", self.t_leaves), ("Me", self.profile)]
                     if T else [("Home", self.s_home), ("Leave", self.s_leave), ("Profile", self.profile)])
        h = Panel(orientation="horizontal", bg=AC, rad=0, size_hint_y=None, height=dp(58), padding=[dp(16), dp(8)], spacing=dp(8))
        t = Label(text="SmartHazri  |  " + ("Teacher" if T else "Student"), font_size=sp(17), bold=True, color=WHITE, halign="left", valign="middle")
        t.bind(size=lambda i, v: setattr(i, "text_size", v))
        h.add_widget(t)
        h.add_widget(RBtn(text="Logout", bg=[1, 1, 1, .2], size_hint_x=None, width=dp(86), on_release=lambda *_: self.logout()))
        self.main.add_widget(h)
        self.holder = BoxLayout()
        self.main.add_widget(self.holder)
        nav = Panel(orientation="horizontal", bg=WHITE, rad=0, size_hint_y=None, height=dp(54))
        self.nbtn = []
        for i, (name, fn) in enumerate(self.tabs):
            b = RBtn(text=name, bg=WHITE, height=dp(54), font_size=sp(12 if len(self.tabs) > 4 else 14), on_release=lambda *_, i=i: self.go(i))
            self.nbtn.append(b)
            nav.add_widget(b)
        self.main.add_widget(nav)
        self.paint_nav()
        self.show(self.tabs[self.tab][1])

    def paint_nav(self):
        for i, b in enumerate(self.nbtn):
            n = self.tabs[i][0]
            b.text = n + (" (%d)" % self.pending() if n == "Leaves" and self.pending() else "")
            b.color = AC if i == self.tab else MU

    def go(self, i):
        self.tab = i
        self.paint_nav()
        self.show(self.tabs[i][1])

    def hero(self, g, u, top, name, sub=""):
        p = Panel(orientation="horizontal", bg=AC, size_hint_y=None, height=dp(116), padding=dp(14), spacing=dp(12))
        p.add_widget(avatar(u, 80))
        c = BoxLayout(orientation="vertical", spacing=dp(2))
        c.add_widget(lbl(top, 13, [.88, .9, 1, 1]))
        c.add_widget(lbl(name, 20, WHITE, True))
        if sub:
            c.add_widget(lbl(sub, 12, [.88, .9, 1, 1]))
        p.add_widget(c)
        g.add_widget(p)

    def selector(self, g, btn, cb):
        c = Card()
        c.add_widget(lbl("Class chuno", 17, bold=True))
        tb = {k: RBtn(text=t, bg=AC if self.grp["inst"] == k else GR, color=WHITE if self.grp["inst"] == k else MU,
                      on_release=lambda *_, k=k: (self.grp.__setitem__("inst", k), self.refresh())) for k, t in (("college", "College"), ("school", "School"))}
        c.add_widget(row(tb["college"], tb["school"]))
        for w in class_fields(self.grp, True, self.refresh):
            c.add_widget(w)
        c.add_widget(RBtn(text=btn, on_release=lambda *_: cb()))
        g.add_widget(c)

    # ---------- teacher ----------
    def t_home(self, g):
        u = self.me
        self.hero(g, u, "Namaste", fullname(u), "Subject: " + (u["subject"] or "-"))
        r = dict(self.db("SELECT st,COUNT(*) FROM att WHERE d=? AND tid=? GROUP BY st", (today(), u["username"])))
        ns = self.db("SELECT COUNT(*) FROM users WHERE role='student'")[0][0]
        grid = GridLayout(cols=2, size_hint_y=None, height=dp(180), spacing=dp(10))
        for v, t, col in ((ns, "Registered students", TX), (sum(r.values()), "Aaj ki hazri li", AC), (r.get("P", 0), "Aaj present", OK), (r.get("A", 0), "Aaj absent", NO)):
            p = Panel(orientation="vertical", padding=dp(14), spacing=dp(2))
            p.add_widget(lbl(v, 30, col, True))
            p.add_widget(lbl(t, 13, MU))
            grid.add_widget(p)
        g.add_widget(grid)
        c = Card()
        c.add_widget(lbl("Kaise use karein", 16, bold=True))
        c.add_widget(lbl("Hazri tab me class chuno, Present/Absent mark karo aur Save dabao.\nHazri sirf AAJ ki hi li ya badli ja sakti hai.\nReport tab me har student ke present/absent din aur percentage milenge.\nStudents tab se naya student add kar sakte ho.", 13, MU))
        g.add_widget(c)
        self.t_cal(g)

    def start_mark(self):
        studs = self.students(self.grp)
        if not studs:
            return msg("Koi student nahi", "Is class me abhi koi student registered nahi hai.")
        me, day = self.me["username"], today()
        saved = dict(self.db("SELECT sid,st FROM att WHERE d=? AND tid=?", (day, me)))
        lv = {x[0] for x in self.db("SELECT sid FROM leaves WHERE status='approved' AND fd<=? AND td>=?", (day, day))}
        self.studs, self.day = studs, day
        self.pend = {s["username"]: saved.get(s["username"]) or ("L" if s["username"] in lv else None) for s in studs}
        self.saved = any(s["username"] in saved for s in studs)
        self.hz = True
        self.refresh()

    def paint(self, btns, cur):
        for v, b in btns.items():
            on = v == cur
            b.bg = ST_COL[v] if on else GR
            b.color = WHITE if on else MU

    def upd(self):
        n = sum(1 for s in self.studs if self.pend.get(s["username"]))
        self.cnt.text = "Marked: %d / %d   |   %s" % (n, len(self.studs), "Saved hai" if self.saved else "Abhi SAVE nahi hua")
        self.cnt.color = OK if self.saved else LV

    def setm(self, sid, v):
        self.pend[sid] = v
        self.saved = False
        self.paint(self.mw[sid], v)
        self.upd()

    def markall(self, v):
        for s in self.studs:
            self.setm(s["username"], v)

    def save_att(self):
        if self.day != today():
            self.hz = False
            self.refresh()
            return msg("Naya din", "Din badal gaya hai. Class dobara chuno.")
        miss = sum(1 for s in self.studs if not self.pend.get(s["username"]))
        if miss:
            return msg("Adhuri hazri", "%d students ka Present/Absent/Leave mark baki hai." % miss)
        self.con.executemany("INSERT OR REPLACE INTO att VALUES(?,?,?,?)", [(self.day, s["username"], self.me["username"], self.pend[s["username"]]) for s in self.studs])
        self.con.commit()
        self.saved = True
        self.upd()
        msg("Saved", "Aaj ki attendance save ho gayi (%d students)." % len(self.studs))

    def t_mark(self, g):
        if self.hz and self.day != today():
            self.hz = False
        if not self.hz:
            return self.selector(g, "Students dikhao", self.start_mark)
        c = Card()
        c.add_widget(lbl("Aaj ki Hazri", 18, bold=True))
        c.add_widget(lbl(dt.date.today().strftime("%d %B %Y, %A"), 14, MU))
        c.add_widget(lbl(glabel(self.grp), 14, AC, True))
        self.cnt = lbl("", 13, MU, True)
        c.add_widget(self.cnt)
        c.add_widget(row(RBtn(text="Sab Present", bg=OK, on_release=lambda *_: self.markall("P")), RBtn(text="Sab Absent", bg=NO, on_release=lambda *_: self.markall("A"))))
        c.add_widget(RBtn(text="Save Attendance", on_release=lambda *_: self.save_att()))
        c.add_widget(RBtn(text="Class badlo", bg=MU, on_release=lambda *_: (setattr(self, "hz", False), self.refresh())))
        g.add_widget(c)
        self.mw = {}
        for s in self.studs:
            c = Card()
            c.add_widget(row(lbl(s["roll"], 13, MU, True, w=64), lbl(fullname(s), 16, TX, True), h=30))
            btns = {v: RBtn(text=ST_TXT[v], font_size=sp(13)) for v in "PAL"}
            for v, b in btns.items():
                b.bind(on_release=lambda *_, sid=s["username"], v=v: self.setm(sid, v))
            self.mw[s["username"]] = btns
            self.paint(btns, self.pend.get(s["username"]))
            c.add_widget(row(*btns.values()))
            g.add_widget(c)
        c = Card()
        c.add_widget(RBtn(text="Save Attendance", on_release=lambda *_: self.save_att()))
        g.add_widget(c)
        self.upd()

    def show_rep(self):
        self.rep = True
        self.refresh()

    def t_report(self, g):
        self.selector(g, "Report dikhao", self.show_rep)
        if not self.rep:
            return self.del_card(g)
        me = self.me["username"]
        studs = self.students(self.grp)
        data = [(s, self.stat(s["username"], me)) for s in studs]
        c = Card()
        c.add_widget(lbl("Attendance Report", 18, bold=True))
        c.add_widget(lbl(glabel(self.grp), 14, AC, True))
        done = [d for d in data if d[1][3]]
        avg = round(sum(d[1][4] for d in done) / len(done)) if done else 0
        c.add_widget(lbl("Students: %d   |   Class average: %d%%   |   75%% se kam: %d" % (len(studs), avg, sum(1 for d in done if d[1][4] < 75)), 13, MU))
        c.add_widget(RBtn(text="CSV file export karo", on_release=lambda *_: self.export(data)))
        g.add_widget(c)
        if not studs:
            c = Card()
            c.add_widget(lbl("Is class me koi student registered nahi hai.", 14, MU))
            g.add_widget(c)
        for s, (p, a, l, t, pc) in data:
            col = NO if pc < 75 and t else OK
            c = Card()
            c.add_widget(row(lbl(s["roll"], 13, MU, True, w=64), lbl(fullname(s), 16, TX, True), lbl("%d%%" % pc if t else "-", 16, col, True, "right", 60), h=30))
            c.add_widget(lbl("Present: %d din   |   Absent: %d din   |   Leave: %d" % (p, a, l), 13, MU))
            b = Bar(size_hint_y=None, height=dp(10), col=col)
            grow(b, pc)
            c.add_widget(b)
            g.add_widget(c)
        self.del_card(g)

    def export(self, data):
        rows = [["Roll", "Naam", "Present", "Absent", "Leave", "Total", "Percent"]]
        for s, (p, a, l, t, pc) in data:
            rows.append([s["roll"], fullname(s), p, a, l, t, "%d%%" % pc if t else "-"])
        for base in ("/storage/emulated/0/Download", self.user_data_dir):
            try:
                path = os.path.join(base, "attendance_report.csv")
                with open(path, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerows(rows)
                return msg("Ho gaya", "File save hui:\n" + path)
            except Exception:
                continue
              msg("Error", "File save nahi ho payi.")

    def t_leaves(self, g):
        rs = self.rows("SELECT l.*,u.name,u.surname,u.roll,u.inst,u.branch,u.year,u.sec,u.batch,u.cls FROM leaves l JOIN users u ON u.username=l.sid "
                       "WHERE l.tid=? OR l.tid='' ORDER BY l.id DESC", (self.me["username"],))
        if not rs:
            c = Card()
            c.add_widget(lbl("Koi leave request nahi.", 14, MU))
            g.add_widget(c)
        for r in rs:
            c = Card()
            c.add_widget(row(lbl(fullname(r), 16, TX, True), lbl(r["status"].upper(), 13, {"pending": LV, "approved": OK, "rejected": NO}[r["status"]], True, "right", 100), h=30))
            c.add_widget(lbl("Roll %s  |  %s" % (r["roll"], glabel(r)), 12, MU))
            c.add_widget(lbl("%s  to  %s" % (r["fd"], r["td"]), 13, AC, True))
            c.add_widget(lbl(r["reason"], 14))
            if r["status"] == "pending":
                c.add_widget(row(RBtn(text="Approve", bg=OK, on_release=lambda *_, i=r["id"]: self.decide(i, True)),
                                 RBtn(text="Reject", bg=NO, on_release=lambda *_, i=r["id"]: self.decide(i, False))))
            g.add_widget(c)

    def decide(self, lid, ok):
        self.db("UPDATE leaves SET status=?,tid=? WHERE id=?", ("approved" if ok else "rejected", self.me["username"], lid))
        self.paint_nav()
        self.refresh()
      # ---------- teacher: calendar, students, delete old data ----------
    def t_cal(self, g):
        me = self.me["username"]
        y, m = self.cm
        pre = "%04d-%02d-" % (y, m)
        agg = {}
        for d, s, n in self.db("SELECT d,st,COUNT(*) FROM att WHERE tid=? AND d LIKE ? GROUP BY d,st", (me, pre + "%")):
            agg.setdefault(d, {})[s] = n
        c = Card()
        c.add_widget(lbl("Attendance Calendar", 16, bold=True))
        c.add_widget(row(small("<", lambda: self.mv(-1)), lbl("%s %d" % (calendar.month_name[m], y), 17, TX, True, "center"), small(">", lambda: self.mv(1))))
        weeks = calendar.monthcalendar(y, m)
        grid = GridLayout(cols=7, size_hint_y=None, height=dp(38) * (len(weeks) + 1), spacing=dp(4))
        for dn in "SMTWTFS":
            grid.add_widget(Label(text=dn, color=MU, bold=True))
        for wk in weeks:
            for d in wk:
                if not d:
                    grid.add_widget(Widget())
                    continue
                k = pre + "%02d" % d
                v = agg.get(k)
                col = [.93, .94, .97, 1]
                if v:
                    t = v.get("P", 0) + v.get("A", 0)
                    pc = v.get("P", 0) * 100 / t if t else 50
                    col = OK if pc >= 75 else LV if pc >= 50 else NO
                grid.add_widget(DayCell(text=str(d), bg=col, color=WHITE if v else TX, font_size=sp(13), on_release=lambda *_, k=k: self.day_info(k)))
        c.add_widget(grid)
        c.add_widget(lbl("Hara: 75%+ present   Narangi: 50-75%   Laal: 50% se kam   Dhusar: hazri nahi li.\nKisi din ko dabao to uski detail milegi.", 12, MU, align="center"))
        g.add_widget(c)

    def day_info(self, k):
        rs = self.rows("SELECT a.st,u.name,u.surname,u.roll,u.inst,u.branch,u.year,u.sec,u.batch,u.cls FROM att a JOIN users u ON u.username=a.sid "
                       "WHERE a.d=? AND a.tid=? ORDER BY u.inst,u.branch,u.year,u.sec,u.cls,length(u.roll),u.roll", (k, self.me["username"]))
        title = dt.date.fromisoformat(k).strftime("%d %B %Y, %A")
        if not rs:
            return msg(title, "Is din aapne koi hazri nahi li.")
        gr = {}
        for r in rs:
            gr.setdefault(glabel(r), []).append(r)
        out = []
        for lab, L in gr.items():
            n = lambda x: sum(1 for r in L if r["st"] == x)
            out.append("%s\nPresent %d | Absent %d | Leave %d" % (lab, n("P"), n("A"), n("L")))
            ab = ["%s (%s)" % (fullname(r), r["roll"]) for r in L if r["st"] == "A"]
            if ab:
                out.append("Absent: " + ", ".join(ab))
            out.append("")
        out.append("Aaj ki hazri Hazri tab se badli ja sakti hai." if k == today() else "Purani date ki attendance badli nahi ja sakti.")
        info(title, "\n".join(out))

    def t_students(self, g):
        st = self.ns
        c = Card()
        c.add_widget(lbl("Naya student add karo", 17, bold=True))
        fld(c, st, "Username (student ke login ke liye)", "username")
        fld(c, st, "Password (4+ akshar)", "pw", password=True)
        fld(c, st, "Naam (First name)", "name")
        fld(c, st, "Surname", "surname")
        fld(c, st, "Mobile number (10 digit)", "mobile", num=True)
        fld(c, st, "Roll number", "roll")
        c.add_widget(lbl("Padhai ka level", 12, MU))
        ib = {k: RBtn(text=t, bg=AC if st["inst"] == k else GR, color=WHITE if st["inst"] == k else MU,
                      on_release=lambda *_, k=k: (st.__setitem__("inst", k), self.refresh())) for k, t in (("college", "College"), ("school", "School"))}
        c.add_widget(row(ib["college"], ib["school"]))
        for w in class_fields(st, False, self.refresh):
            c.add_widget(w)
        c.add_widget(RBtn(text="+ Student add karo", on_release=lambda *_: self.add_student()))
        g.add_widget(c)
        studs = self.students(st)
        c = Card()
        c.add_widget(lbl("Is class ke students (%d)" % len(studs), 16, bold=True))
        c.add_widget(lbl(glabel(st), 13, AC, True))
        g.add_widget(c)
        for s in studs:
            c = Card()
            c.add_widget(row(lbl(s["roll"], 13, MU, True, w=64), lbl(fullname(s), 16, TX, True), h=30))
            c.add_widget(lbl("Username: %s   |   Mobile: %s" % (s["username"], s["mobile"]), 12, MU))
            c.add_widget(row(RBtn(text="Password reset", bg=MU, on_release=lambda *_, u=s["username"]: self.reset_pw(u)),
                             RBtn(text="Hatao", bg=NO, on_release=lambda *_, u=s: ask("Student hatao?", "%s aur uski saari attendance hamesha ke liye delete ho jayegi." % fullname(u), lambda: self.rm_student(u["username"])))))
            g.add_widget(c)

    def add_student(self):
        st = self.ns
        st["pw2"], st["role"] = st["pw"], "student"
        if self.do_register(st, True):
            keep = {k: st[k] for k in ("inst", "branch", "branch_o", "year", "sec", "batch", "cls")}
            self.ns = dict(reg_state(), **keep)
            msg("Done", "Student add ho gaya. Wo apne username/password se login kar sakta hai.")
            self.refresh()

    def reset_pw(self, sid):
        def done(p):
            if len(p) < 4:
                return msg("Dhyan do", "Password kam se kam 4 akshar ka ho.")
            self.db("UPDATE users SET pw=? WHERE username=?", (hp(p), sid))
            msg("Done", "Password badal gaya.")
        prompt("Naya password", "Naya password (4+ akshar)", done)

    def rm_student(self, sid):
        u = self.urow(sid)
        for t in ("users WHERE username", "att WHERE sid", "leaves WHERE sid"):
            self.db("DELETE FROM " + t + "=?", (sid,))
        if u and u["photo"] and os.path.exists(u["photo"]):
            try:
                os.remove(u["photo"])
            except Exception:
                pass
        self.hz = False
        self.refresh()

    def del_card(self, g):
        me = self.me["username"]
        mn = self.db("SELECT MIN(d) FROM att WHERE tid=?", (me,))[0][0] or today()
        old = (dt.date.today() - dt.timedelta(days=365)).isoformat()
        c = Card()
        c.add_widget(lbl("Purani attendance delete karo", 16, bold=True))
        c.add_widget(lbl("Upar chuni hui class ki, sirf aapki li hui attendance, is date range me delete hogi (storage khali karne ke liye). Default: 1 saal se purani.", 12, MU))
        f, t = inp("Se (YYYY-MM-DD)", mn), inp("Tak (YYYY-MM-DD)", max(min(old, today()), mn))
        c.add_widget(f)
        c.add_widget(t)

        def go(*_):
            if not (vd(f.text) and vd(t.text)) or t.text < f.text:
                return msg("Dhyan do", "Dates (YYYY-MM-DD) sahi bharo, 'Tak' date 'Se' se baad ki ho.")
            ids = [s["username"] for s in self.students(self.grp)]
            if not ids:
                return msg("Koi student nahi", "Is class me koi student registered nahi hai.")
            mk = ",".join("?" * len(ids))
            n = self.db("SELECT COUNT(*) FROM att WHERE tid=? AND d BETWEEN ? AND ? AND sid IN (%s)" % mk, [me, f.text, t.text] + ids)[0][0]
            if not n:
                return msg("Kuch nahi mila", "Is range me is class ki koi attendance nahi hai.")
            ask("Pakka delete?", "%s\n%s se %s tak ki %d entries delete hongi. Ye wapas nahi aa sakti." % (glabel(self.grp), f.text, t.text, n),
                lambda: self.do_del(me, f.text, t.text, ids, mk))

        c.add_widget(RBtn(text="Delete karo", bg=NO, on_release=go))
        g.add_widget(c)

    def do_del(self, me, f, t, ids, mk):
        self.db("DELETE FROM att WHERE tid=? AND d BETWEEN ? AND ? AND sid IN (%s)" % mk, [me, f, t] + ids)
        self.db("VACUUM")
        self.hz = False
        msg("Ho gaya", "Purani attendance delete ho gayi aur storage saaf kar di gayi.")
        self.refresh()

    # ---------- student ----------
    def mv(self, n):
        y, m = self.cm
        m += n
        if m < 1:
            m, y = 12, y - 1
        if m > 12:
            m, y = 1, y + 1
        self.cm = (y, m)
        self.refresh()

    def s_home(self, g):
        u = self.me
        uid = u["username"]
        if not hasattr(self, "cm"):
            t = dt.date.today()
            self.cm = (t.year, t.month)
        p, a, l, t, pc = self.stat(uid)
        self.hero(g, u, "Welcome", fullname(u), "Roll %s  |  %s" % (u["roll"], glabel(u)))
        col = NO if pc < 75 and t else OK
        c = Card(orientation="horizontal", spacing=dp(14))
        ring = Ring(size_hint=(None, None), size=(dp(120), dp(120)), col=col)
        Clock.schedule_once(lambda d: Animation(value=pc, d=1.1, t="out_cubic").start(ring), .3)
        c.add_widget(ring)
        info = BoxLayout(orientation="vertical", spacing=dp(2))
        info.add_widget(lbl("Present: %d din" % p, 15, OK, True))
        info.add_widget(lbl("Absent: %d din" % a, 15, NO, True))
        info.add_widget(lbl("Leave: %d" % l, 15, LV, True))
        info.add_widget(lbl("Total: %d" % t, 13, MU))
        c.add_widget(info)
        g.add_widget(c)
        if pc < 75 and t:
            w = Card(bg=[1, .93, .93, 1])
            w.add_widget(lbl("Attendance 75%% se kam hai! Lagataar %d class attend karo to 75%% ho jayegi." % max(1, 3 * t - 4 * p), 14, NO, True))
            g.add_widget(w)
        per = {}
        for tid, s, n in self.db("SELECT tid,st,COUNT(*) FROM att WHERE sid=? GROUP BY tid,st", (uid,)):
            per.setdefault(tid, {})[s] = n
        if per:
            c = Card()
            c.add_widget(lbl("Subject-wise attendance", 16, bold=True))
            for tid, v in per.items():
                tr = self.urow(tid)
                nm = (tr["subject"] or fullname(tr)) if tr else tid
                tp, ta = v.get("P", 0), v.get("A", 0)
                ppc = round(tp * 100 / (tp + ta)) if tp + ta else 0
                c.add_widget(row(lbl(nm, 14, TX, True), lbl("%d%%" % ppc, 14, NO if ppc < 75 else OK, True, "right", 56), h=28))
                c.add_widget(lbl("Present %d  |  Absent %d" % (tp, ta), 12, MU))
                b = Bar(size_hint_y=None, height=dp(8), col=NO if ppc < 75 else OK)
                grow(b, ppc)
                c.add_widget(b)
            g.add_widget(c)
        dd = {}
        for d, s in self.db("SELECT d,st FROM att WHERE sid=?", (uid,)):
            dd.setdefault(d, set()).add(s)
        ld = set()
        for fd, td in self.db("SELECT fd,td FROM leaves WHERE sid=? AND status='approved'", (uid,)):
            d, e = dt.date.fromisoformat(fd), dt.date.fromisoformat(td)
            while d <= e and len(ld) < 800:
                ld.add(d.isoformat())
                d += dt.timedelta(days=1)

        def dstat(k):
            s = dd.get(k)
            return ("A" if "A" in s else "P" if "P" in s else "L") if s else ("L" if k in ld else None)

        y, m = self.cm
        c = Card()
        c.add_widget(row(small("<", lambda: self.mv(-1)), lbl("%s %d" % (calendar.month_name[m], y), 17, TX, True, "center"), small(">", lambda: self.mv(1))))
        weeks = calendar.monthcalendar(y, m)
        grid = GridLayout(cols=7, size_hint_y=None, height=dp(38) * (len(weeks) + 1), spacing=dp(4))
        for dn in "SMTWTFS":
            grid.add_widget(Label(text=dn, color=MU, bold=True))
        for wk in weeks:
            for d in wk:
                if not d:
                    grid.add_widget(Widget())
                    continue
                s = dstat("%04d-%02d-%02d" % (y, m, d))
                grid.add_widget(Cell(text=str(d), bg=ST_COL.get(s, [.93, .94, .97, 1]), color=WHITE if s else TX, font_size=sp(13)))
        c.add_widget(grid)
        c.add_widget(lbl("Hara = Present   Laal = Absent   Narangi = Leave", 12, MU, align="center"))
        g.add_widget(c)

    def s_leave(self, g):
        c = Card()
        c.add_widget(lbl("Leave ke liye apply karo", 16, bold=True))
        f, t, r = inp("Se (YYYY-MM-DD)", today()), inp("Tak (YYYY-MM-DD)", today()), inp("Reason")
        for w in (f, t, r):
            c.add_widget(w)

        def send(*_):
            if not (vd(f.text) and vd(t.text)) or t.text < f.text or not r.text.strip():
                return msg("Dhyan do", "Dates (YYYY-MM-DD) aur reason sahi bharo.")
            self.db("INSERT INTO leaves(sid,tid,fd,td,reason,status) VALUES(?,?,?,?,?,'pending')", (self.me["username"], self.me["mentor"], f.text, t.text, r.text.strip()))
            msg("Done", "Request bhej di gayi.")
            self.refresh()

        c.add_widget(RBtn(text="Request bhejo", on_release=send))
        g.add_widget(c)
        for fd, td, rs, st in self.db("SELECT fd,td,reason,status FROM leaves WHERE sid=? ORDER BY id DESC", (self.me["username"],)):
            c = Card()
            c.add_widget(row(lbl("%s  to  %s" % (fd, td), 14, TX, True), lbl(st.upper(), 13, {"pending": LV, "approved": OK, "rejected": NO}[st], True, "right", 100), h=30))
            c.add_widget(lbl(rs, 13, MU))
            g.add_widget(c)

    # ---------- profile (teacher + student) ----------
    def profile(self, g):
        u = self.me
        c = Card()
        c.add_widget(row(avatar(u, 90), RBtn(text="Photo badlo", bg=MU, pos_hint={"center_y": .5}, on_release=lambda *_: self.pick_photo(self.new_photo)), h=96))
        c.add_widget(lbl(fullname(u), 20, TX, True))
        lines = ["Username: " + u["username"], "Mobile: " + u["mobile"]]
        if u["role"] == "teacher":
            lines += ["Subject: " + (u["subject"] or "-"), "Department: " + (u["dept"] or "-"), "Employee ID: " + (u["empid"] or "-")]
        else:
            m = self.urow(u["mentor"]) if u["mentor"] else None
            lines += ["Roll no: " + u["roll"], "Class: " + glabel(u), "Mentor: " + (fullname(m) if m else "-")]
        for x in lines:
            c.add_widget(lbl(x, 14, MU))
        g.add_widget(c)
        c = Card()
        c.add_widget(lbl("Password badlo", 16, bold=True))
        o, n = inp("Purana password", password=True), inp("Naya password", password=True)
        c.add_widget(o)
        c.add_widget(n)

        def ch(*_):
            if not chk(o.text, u["pw"]):
                return msg("Galat", "Purana password galat hai.")
            if len(n.text) < 4:
                return msg("Dhyan do", "Naya password kam se kam 4 akshar ka ho.")
            self.db("UPDATE users SET pw=? WHERE username=?", (hp(n.text), u["username"]))
            self.me = self.urow(u["username"])
            msg("Done", "Password badal gaya.")
            self.refresh()

        c.add_widget(RBtn(text="Update", on_release=ch))
        g.add_widget(c)

    def new_photo(self, src):
        ph = self.save_photo(src, self.me["username"])
        if not ph:
            return msg("Error", "Photo save nahi ho payi.")
        old = self.me["photo"]
        self.db("UPDATE users SET photo=? WHERE username=?", (ph, self.me["username"]))
        if old and os.path.exists(old):
            try:
                os.remove(old)
            except Exception:
                pass
        self.me = self.urow(self.me["username"])
        self.refresh()


if __name__ == "__main__":
    SmartHazri().run()
