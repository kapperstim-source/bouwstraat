#!/usr/bin/env python3
"""deploy.py — zet een demo online op Cloudflare Pages, als eigen branch van één project.

    export CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=...
    python3 deploy.py klanten/<map> [--project voorbeelden] [--slug frank-echten]

Resultaat: https://<slug>.<project>.pages.dev (branch-alias, blijft staan tot je hem
verwijdert). Eén project voor alle demo's, dus de limiet van 100 projecten per account
speelt niet; het aantal branches is onbeperkt. Direct upload via wrangler, geen build.

Waarom Cloudflare Pages en niet Vercel: het gratis Hobby-plan van Vercel is volgens de
eigen docs "restricted to non-commercial, personal use only"; verkoopdemo's zijn
commercieel gebruik. Cloudflare Pages heeft die regel niet.
"""
import argparse, json, os, re, signal, subprocess, sys, time, urllib.request, ssl

CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
WRANGLER = ["npx", "--yes", "wrangler@4"]


def slug_van(tekst, maximum=28):
    s = re.sub(r"[^a-z0-9]+", "-", (tekst or "").lower()).strip("-")
    s = re.sub(r"-(bv|vof|b-v|v-o-f|nl)$", "", s)
    return s[:maximum].strip("-") or "demo"


def wrangler(args, env, timeout=300):
    """Draait wrangler zonder stdin (geen vragen), in een eigen procesgroep, en ruimt bij een
    time-out de hele groep op zodat niets blijft hangen."""
    p = subprocess.Popen(WRANGLER + args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        uit, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except Exception:
            pass
        uit, _ = p.communicate()
        return 124, (uit or "") + "\n[time-out na %d s]" % timeout
    return p.returncode, uit or ""


def omgeving(config_pad=None):
    """Token en account-id uit de omgeving, of anders uit config.json (zo hoeft het token
    nooit op een commandoregel te staan)."""
    env = dict(os.environ)
    if (not env.get("CLOUDFLARE_API_TOKEN") or not env.get("CLOUDFLARE_ACCOUNT_ID")):
        for pad in [config_pad, "config.json", os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")]:
            if pad and os.path.exists(pad):
                try:
                    c = json.load(open(pad, encoding="utf-8-sig"))
                    env["CLOUDFLARE_API_TOKEN"] = c.get("cloudflare_api_token") or env.get("CLOUDFLARE_API_TOKEN", "")
                    env["CLOUDFLARE_ACCOUNT_ID"] = c.get("cloudflare_account_id") or env.get("CLOUDFLARE_ACCOUNT_ID", "")
                    break
                except Exception:
                    pass
    if not env.get("CLOUDFLARE_API_TOKEN") or env["CLOUDFLARE_API_TOKEN"] == "VUL-IN" or not env.get("CLOUDFLARE_ACCOUNT_ID"):
        raise SystemExit("CLOUDFLARE_API_TOKEN en CLOUDFLARE_ACCOUNT_ID ontbreken (omgeving of config.json)")
    env["WRANGLER_SEND_METRICS"] = "false"
    env.setdefault("CI", "1")
    return env


def project_bestaat(project, env):
    rc, uit = wrangler(["pages", "project", "list"], env, timeout=120)
    return rc == 0 and re.search(r"\b" + re.escape(project) + r"\b", uit) is not None


def maak_project(project, env, log=print):
    if project_bestaat(project, env):
        return
    rc, uit = wrangler(["pages", "project", "create", project, "--production-branch", "main"], env, timeout=120)
    if rc != 0 and "already exists" not in uit:
        raise RuntimeError("project aanmaken mislukt: " + uit[-800:])
    log(f"  project {project} aangemaakt")
    # productie-branch één keer vullen, zodat <project>.pages.dev geen 404 geeft
    tmp = "/tmp/pages-startpagina"
    os.makedirs(tmp, exist_ok=True)
    open(os.path.join(tmp, "index.html"), "w").write("<!doctype html><html lang=nl><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><meta name=robots content=noindex><title>Voorbeelden</title><body style='font-family:system-ui;padding:3rem'><p>Voorbeeldontwerpen van Tim Kappers. Elk voorbeeld heeft een eigen adres.</p></body></html>")
    open(os.path.join(tmp, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")
    wrangler(["pages", "deploy", tmp, "--project-name", project, "--branch", "main", "--commit-dirty=true"], env)


def bereikbaar(url, pogingen=10):
    for i in range(pogingen):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bouwstraat-check"})
            with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
                if r.status == 200 and b"<html" in r.read(4000).lower():
                    return True
        except Exception:
            pass
        time.sleep(3 + i * 2)
    return False


def deploy(map_klant, project="voorbeelden", slug=None, log=print, config_pad=None):
    env = omgeving(config_pad)
    web = os.path.join(map_klant, "web")
    if not os.path.exists(os.path.join(web, "index.html")):
        raise RuntimeError(f"geen web/index.html in {map_klant}")
    if not slug:
        try:
            c = json.load(open(os.path.join(map_klant, "content.json"), encoding="utf-8"))
            slug = slug_van(c.get("domein", "").split(".")[0] or c.get("naam"))
        except Exception:
            slug = slug_van(os.path.basename(map_klant.rstrip("/")))
    maak_project(project, env, log)
    rc, uit = wrangler(["pages", "deploy", web, "--project-name", project, "--branch", slug, "--commit-dirty=true"], env)
    if rc != 0:
        raise RuntimeError("deploy mislukt: " + uit[-1200:])
    m = re.search(r"https://[\w.-]+\.pages\.dev", uit)
    url_hash = m.group(0) if m else None
    url = f"https://{slug}.{project}.pages.dev"
    ok = bereikbaar(url)
    if not ok and url_hash and bereikbaar(url_hash, 3):
        log(f"  branch-alias nog niet bereikbaar, val terug op {url_hash}")
        url = url_hash
    uitkomst = {"url": url, "url_hash": url_hash, "slug": slug, "project": project, "bereikbaar": ok or bool(url_hash)}
    json.dump(uitkomst, open(os.path.join(map_klant, "deploy.json"), "w"), indent=1)
    log(f"  online: {url}" + ("" if ok else "  (nog niet bevestigd bereikbaar)"))
    return uitkomst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("--project", default="voorbeelden"); ap.add_argument("--slug")
    a = ap.parse_args()
    print(json.dumps(deploy(a.map, a.project, a.slug, log=lambda s: print(s, file=sys.stderr)), indent=1))


if __name__ == "__main__":
    main()
