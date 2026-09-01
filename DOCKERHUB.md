# Open Hardware Manager

Match open hardware designs to the workshops that can actually build them.

OHM reads OKH design manifests and OKW facility records, works out which
facilities can make which designs, and gives you the supply tree that shows
how. It federates: your node holds your data, and shares only what you choose.

- **Site** — https://www.openhardwaremanager.org
- **Docs** — https://www.openhardwaremanager.org/docs/
- **Source** — https://github.com/helpfulengineering/supply-graph-ai

## Install a node

You need Docker, and nothing else. Download the installer, check it, run it:

```bash
curl -fsSLO https://openhardwaremanager.org/install.sh
curl -fsSLO https://github.com/helpfulengineering/supply-graph-ai/releases/latest/download/install.sh.sha256
sha256sum -c install.sh.sha256
sh install.sh
```

The one-liner is there if you prefer it:

```bash
curl -fsSL https://openhardwaremanager.org/install.sh | sh
```

We show the checked form first on purpose. OHM exists to make supply chains
inspectable, and it would be odd to ask you to pipe a remote script into your
shell unread. On macOS, `shasum -a 256 -c` replaces `sha256sum -c`.

## Install, then configure

They are two steps, deliberately. The installer finishes at a healthy node on
local storage, and everything needing a decision happens afterwards in the
running node — which is what lets the install itself ask nothing.

It prints a URL and an admin key. **Save the key: it is shown once.**

1. Open the URL, go to `/settings/session`, paste the key.
2. Point the node at real storage at `/settings/storage`, if you want to. Local
   storage works meanwhile, and switching later can bring existing data with it.

## Running the container by hand

The installer starts two containers — this API image, and
`touchthesun/openhardwaremanager-frontend`, which serves the web interface and
reverse-proxies `/v1` to the API. To run the API alone:

```bash
docker run -p 8001:8001 \
  -e STORAGE_PROVIDER=local \
  -e API_KEYS=your-admin-key \
  -e OHM_ENCRYPTION_SALT=some-random-value \
  -e OHM_ENCRYPTION_PASSWORD=another-random-value \
  touchthesun/openhardwaremanager:latest
```

`OHM_ENCRYPTION_*` are not optional in practice: credential storage refuses to
operate under its built-in defaults, so a node started without them cannot be
given storage or LLM credentials afterwards.

The API is then at `http://localhost:8001`, with `/health` for liveness and
`/docs` for the OpenAPI browser.

## Tags

Released versions are tagged `X.Y.Z`, and `latest` follows the newest release.
Images are built for `linux/amd64` and `linux/arm64`.

## Licence

AGPL-3.0. See the repository for details.
