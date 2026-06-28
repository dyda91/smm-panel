import json
import os
from dotenv import load_dotenv
from instagram import get_feed, get_profile
from smm import add_order

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
MORETHANPANEL_API_KEY = os.getenv("MORETHANPANEL_API_KEY")

PROCESSED_FILE = "processed_posts.json"


def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return {}
    try:
        with open(PROCESSED_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_processed(data):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(data, f, indent=4)


def process_account(account):
    if not account.instagram_id:
        print("Conta sem instagram_id")
        return None

    rapid_key = account.rapid_key or RAPIDAPI_KEY
    rapid_host = account.rapid_host or RAPIDAPI_HOST
    smm_key = account.smm_key or MORETHANPANEL_API_KEY

    stats = {"orders": 0, "errors": 0, "followers": 0, "username": ""}

    print("====================")
    print("CONTA:", account.instagram_id)
    print("====================")

    profile = get_profile(account.instagram_id, rapid_key, rapid_host)
    if not profile:
        print("Perfil vazio — abortando")
        return stats

    username = profile.get("username", "")
    followers = int(profile.get("follower_count", 0))
    stats["username"] = username
    stats["followers"] = followers
    print("USUARIO:", username)
    print("SEGUIDORES:", followers)

    if followers <= 0:
        print("Seguidores <= 0, abortando")
        return stats

    processed = load_processed()
    account_key = str(account.instagram_id)
    if account_key not in processed:
        processed[account_key] = []

    if account.followers_enabled and account.followers_service:
        quantidade = int(followers * float(account.followers_pct) / 100)
        if quantidade > 0:
            profile_link = f"https://instagram.com/{username}"
            print("PEDIDO FOLLOWERS:", profile_link, quantidade)
            try:
                retorno = add_order(
                    smm_key=smm_key,
                    service_id=account.followers_service,
                    link=profile_link,
                    quantity=quantidade
                )
                stats["orders"] += 1
                print("RESPOSTA FOLLOWERS:", retorno)
            except Exception as e:
                stats["errors"] += 1
                print("ERRO FOLLOWERS:", e)
        else:
            print("Quantidade seguidores = 0, pulando")

    print("Buscando feed...")
    feed = get_feed(account.instagram_id, rapid_key, rapid_host)

    if isinstance(feed, dict):
        print("DEBUG - CHAVES FEED:", list(feed.keys()))
    else:
        print("DEBUG - TIPO FEED:", type(feed))

    posts = []
    if isinstance(feed, dict):
        posts = feed.get("items") or feed.get("data", {}).get("items") or []
        if not posts:
            for key in ("items", "posts", "media", "edges", "results"):
                val = feed.get(key)
                if isinstance(val, list):
                    posts = val
                    break
                if isinstance(val, dict):
                    for subkey in ("items", "edges", "nodes"):
                        sub = val.get(subkey)
                        if isinstance(sub, list):
                            posts = sub
                            break
                    if posts:
                        break
    elif isinstance(feed, list):
        posts = feed

    print("TOTAL POSTS ENCONTRADOS:", len(posts))

    if not processed[account_key]:
        posts = posts[:5]
        print("PRIMEIRA EXECUÇÃO — limitando aos 5 posts mais recentes")

    for post in posts:
        post_id = str(
            post.get("id")
            or post.get("pk")
            or post.get("node", {}).get("id")
            or ""
        )
        if not post_id:
            print("Post sem ID, pulando")
            continue

        if post_id in processed[account_key]:
            continue

        shortcode = (
            post.get("code")
            or post.get("shortcode")
            or post.get("node", {}).get("shortcode")
        )
        if not shortcode:
            print("Post sem shortcode, pulando — ID:", post_id)
            continue

        post_link = f"https://instagram.com/p/{shortcode}/"
        print("NOVO POST:", post_link)

        services = [
            (account.likes_enabled, account.likes_service, account.likes_pct, "likes"),
            (account.views_enabled, account.views_service, account.views_pct, "views"),
            (account.shares_enabled, account.shares_service, account.shares_pct, "shares"),
            (account.saves_enabled, account.saves_service, account.saves_pct, "saves"),
        ]

        sucesso = True

        for enabled, service_id, pct, nome in services:
            if not enabled:
                print(f"  {nome}: desabilitado")
                continue
            if not service_id:
                print(f"  {nome}: sem service_id")
                continue

            quantidade = int(followers * float(pct) / 100)
            if quantidade <= 0:
                print(f"  {nome}: quantidade 0")
                continue

            print(f"  CRIANDO {nome}: service={service_id}, qty={quantidade}, link={post_link}")
            try:
                retorno = add_order(
                    smm_key=smm_key,
                    service_id=service_id,
                    link=post_link,
                    quantity=quantidade
                )
                stats["orders"] += 1
                print(f"  RESPOSTA {nome}:", retorno)
            except Exception as e:
                sucesso = False
                stats["errors"] += 1
                print(f"  ERRO {nome}:", e)

        if sucesso:
            processed[account_key].append(post_id)
            print("  POST MARCADO COMO PROCESSADO")
        else:
            print("  POST NÃO marcado (erro em algum serviço)")

    save_processed(processed)
    print("Monitor finalizado para", account.instagram_id)
    return stats
