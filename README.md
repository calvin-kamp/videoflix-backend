# Videoflix API

Backend for Videoflix, a video streaming platform. Users register with their
email, activate the account through a link in an activation email and can then
browse the catalogue and stream movies. Uploaded videos are converted in the
background into HLS streams in three resolutions. The project is a Django REST
Framework API; a client application talks to it over HTTP.

- **Framework:** Django 6.1 with Django REST Framework 3.18
- **Authentication:** JWT (SimpleJWT) stored in `HttpOnly` cookies
- **Database:** PostgreSQL, started as a container
- **Background jobs:** Redis and django-rq (emails and video conversion)
- **Video processing:** ffmpeg, HLS in 480p, 720p and 1080p
- **Runtime:** Python 3.12 inside Docker, served by gunicorn

---

## Table of contents

- [Quick start](#quick-start)
- [Try the API](#try-the-api)
- [Admin panel](#admin-panel)
- [Useful commands](#useful-commands)
- [Configuration](#configuration)
- [Before deploying](#before-deploying)
- [Project layout](#project-layout)
- [How a video is processed](#how-a-video-is-processed)
- [Emails](#emails)
- [Authentication](#authentication)
- [Permissions](#permissions)
- [API reference](#api-reference)
- [Tests](#tests)
- [Troubleshooting](#troubleshooting)

---

## Quick start

**Requirements:** [Docker](https://docs.docker.com/get-docker/) with Docker
Compose v2 and an SMTP account for sending emails. ffmpeg, PostgreSQL and Redis
run inside the containers, so nothing else has to be installed on your machine.

Get the code:

```bash
git clone https://github.com/calvin-kamp/videoflix-backend.git
cd videoflix-backend
```

Create the `.env` file from the template:

**Windows (PowerShell)**

```powershell
Copy-Item .env.template .env
```

**macOS / Linux**

```bash
cp .env.template .env
```

Open `.env` and fill in the `EMAIL_*` values and `DEFAULT_FROM_EMAIL` with the
data of your SMTP account. Choose your own values for `DB_NAME`, `DB_USER` and
`DB_PASSWORD`. All other values of the template work for local development as
they are, see [Configuration](#configuration).

Build and start the containers:

```bash
docker compose up --build
```

The API is now available at `http://localhost:8000/api/`.

On every start the container waits for PostgreSQL, collects the static files,
applies the migrations, creates the superuser from the `DJANGO_SUPERUSER_*`
values (if it does not exist yet) and starts the RQ worker next to gunicorn. The
project folder is mounted into the container and gunicorn reloads on code
changes.

Every command of this README is run from the project root, the folder that
contains `manage.py`.

---

## Try the API

Register, activate the account, log in and load the video list. The login sets
the tokens as cookies, so the following requests have to reuse them: PowerShell
keeps them in a session variable, curl in a cookie file. Postman works as well
and stores the cookies by itself.

The registration response contains the user id and the activation token, so the
account can be activated without opening the email. The activation URL expects
the user id base64-encoded (`uidb64`).

**Windows (PowerShell)**

Use `Invoke-RestMethod`. The `curl` command of PowerShell is something else and
does not accept the bash examples.

```powershell
# 1. Register
$register = @{
    email              = "demo@example.com"
    password           = "S3cure-Passw0rd!"
    confirmed_password = "S3cure-Passw0rd!"
} | ConvertTo-Json

$account = Invoke-RestMethod -Uri "http://localhost:8000/api/register/" -Method Post -ContentType "application/json" -Body $register

# 2. Activate the account with the id and token of the response
$uid = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("$($account.user.id)")).TrimEnd("=")

Invoke-RestMethod -Uri "http://localhost:8000/api/activate/$uid/$($account.token)/"

# 3. Log in; the cookies are stored in $session
$login = @{ email = "demo@example.com"; password = "S3cure-Passw0rd!" } | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/login/" -Method Post -ContentType "application/json" -Body $login -SessionVariable session

# 4. List all videos
Invoke-RestMethod -Uri "http://localhost:8000/api/video/" -WebSession $session | ConvertTo-Json -Depth 3

# 5. Load the 720p playlist of the video with id 1
Invoke-WebRequest -Uri "http://localhost:8000/api/video/1/720p/index.m3u8" -WebSession $session | Select-Object -ExpandProperty Content
```

**macOS / Linux**

```bash
# 1. Register; note "id" and "token" of the response
curl -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "S3cure-Passw0rd!", "confirmed_password": "S3cure-Passw0rd!"}'

# 2. Activate the account; replace 2 with the id and <token> with the token
UIDB64=$(printf '%s' 2 | base64 | tr -d '=')
curl "http://localhost:8000/api/activate/$UIDB64/<token>/"

# 3. Log in; the cookies are stored in cookies.txt
curl -c cookies.txt -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "S3cure-Passw0rd!"}'

# 4. List all videos
curl -b cookies.txt http://localhost:8000/api/video/

# 5. Load the 720p playlist of the video with id 1
curl -b cookies.txt http://localhost:8000/api/video/1/720p/index.m3u8
```

Expected response of the activation: `{"message":"Account successfully activated."}`.
The registration only works once per email; use another email for a second
run. The login response contains no tokens, they are only in the cookies. The
video list stays empty until a video is uploaded in the
[Admin panel](#admin-panel). All endpoints are described in the
[API reference](#api-reference).

---

## Admin panel

The container creates a superuser on start from `DJANGO_SUPERUSER_USERNAME`,
`DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`. To create another one:

```bash
docker compose exec web python manage.py createsuperuser
```

The panel is reachable at `http://localhost:8000/admin/`. Log in with the
username, not the email. There you manage the users and upload videos: create a
video with title, description, category and the video file. The thumbnail is
optional; without one, a frame of the video is used. Saving starts the
conversion, see [How a video is processed](#how-a-video-is-processed).

The queue of the RQ worker, including failed jobs and their errors, is shown at
`http://localhost:8000/django-rq/` (staff login required).

---

## Useful commands

```bash
# Follow the logs of the API and the RQ worker
docker compose logs -f web

# Create migrations after a model change
docker compose exec web python manage.py makemigrations

# Run the migrations manually
docker compose exec web python manage.py migrate

# Open a Django shell
docker compose exec web python manage.py shell

# Run the tests
docker compose exec web python manage.py test

# Stop the containers
docker compose down

# Stop the containers and delete the database, Redis data and uploaded media
docker compose down -v
```

---

## Configuration

All settings are environment variables. They are set in the `.env` file, which
is created from `.env.template` (see [Quick start](#quick-start)). The template
lists every variable with a value that works for local development; the
variables are explained here.

| Variable                       | Required | Example                                 | Purpose                                                                                 |
| ------------------------------ | -------- | --------------------------------------- | --------------------------------------------------------------------------------------- |
| `DJANGO_SUPERUSER_USERNAME`    | no       | `admin`                                 | Username of the superuser that is created on start.                                     |
| `DJANGO_SUPERUSER_PASSWORD`    | no       | `adminpassword`                         | Password of that superuser.                                                             |
| `DJANGO_SUPERUSER_EMAIL`       | no       | `admin@example.com`                     | Email of that superuser.                                                                |
| `SECRET_KEY`                   | yes      | `k3j...`                                | Django's cryptographic key, also signs the JWTs. No default, the server needs it.       |
| `DEBUG`                        | no       | `True`                                  | Debug mode. Defaults to `False`; never enable it in production.                         |
| `ALLOWED_HOSTS`                | no       | `localhost,127.0.0.1`                   | Comma-separated hostnames the server answers for.                                       |
| `CSRF_TRUSTED_ORIGINS`         | no       | `http://localhost:5500`                 | Comma-separated origins of the client. Used for CSRF and as the CORS allow list.        |
| `DB_NAME`                      | yes      | `videoflix`                             | Name of the database the `db` container creates.                                        |
| `DB_USER`                      | yes      | `videoflix`                             | Database user.                                                                          |
| `DB_PASSWORD`                  | yes      | `choose-a-password`                     | Database password.                                                                      |
| `DB_HOST`                      | no       | `db`                                    | Host of the database. `db` inside Docker.                                               |
| `DB_PORT`                      | no       | `5432`                                  | Port of the database.                                                                   |
| `REDIS_HOST`                   | no       | `redis`                                 | Host of Redis for the RQ worker.                                                        |
| `REDIS_PORT`                   | no       | `6379`                                  | Port of Redis.                                                                          |
| `REDIS_DB`                     | no       | `0`                                     | Redis database of the RQ queue.                                                         |
| `REDIS_LOCATION`               | no       | `redis://redis:6379/1`                  | Redis URL of the Django cache.                                                          |
| `EMAIL_HOST`                   | yes      | `smtp.example.com`                      | SMTP server.                                                                            |
| `EMAIL_PORT`                   | no       | `587`                                   | SMTP port.                                                                              |
| `EMAIL_HOST_USER`              | yes      | `mail@example.com`                      | SMTP username.                                                                          |
| `EMAIL_HOST_PASSWORD`          | yes      | `app-password`                          | SMTP password.                                                                          |
| `EMAIL_USE_TLS`                | no       | `True`                                  | Use STARTTLS (usually port `587`).                                                      |
| `EMAIL_USE_SSL`                | no       | `False`                                 | Use SSL (usually port `465`). Must not be `True` together with `EMAIL_USE_TLS`.         |
| `DEFAULT_FROM_EMAIL`           | no       | `Videoflix <mail@example.com>`          | Sender of the emails. Falls back to `EMAIL_HOST_USER`.                                  |
| `FRONTEND_URL`                 | no       | `http://127.0.0.1:5500`                 | Base URL of the client. The links in the emails point there.                            |
| `FRONTEND_ACTIVATION_PATH`     | no       | `pages/auth/activate.html`              | Page of the client that activates the account.                                          |
| `FRONTEND_PASSWORD_RESET_PATH` | no       | `pages/auth/confirm_password.html`      | Page of the client that sets the new password.                                          |
| `AUTH_COOKIE_SECURE`           | no       | `False`                                 | `True` sends the auth cookies only over HTTPS. Defaults to the opposite of `DEBUG`.     |
| `FFMPEG_BINARY`                | no       | `ffmpeg`                                | Path of the ffmpeg executable. The Docker image contains ffmpeg.                        |

The `db` container takes its database name, user and password from `DB_NAME`,
`DB_USER` and `DB_PASSWORD`, so the API and the database always use the same
values.

`CSRF_TRUSTED_ORIGINS` has to contain the exact origin the client is served
from, including protocol and port.

The links in the emails are built as
`FRONTEND_URL/<path>?uid=<uidb64>&token=<token>`. The client reads both
parameters and calls the matching API endpoint.

The server will not start without a `SECRET_KEY`.

---

## Before deploying

The Docker setup is meant for development: gunicorn runs with `--reload` and
Django serves the uploaded media itself, which it only does with `DEBUG=True`.
For a public server, set in `.env`:

- `DEBUG=False`; then serve `/media/` (thumbnails) through a web server such as
  nginx
- serve the API over HTTPS; `AUTH_COOKIE_SECURE` then defaults to `True`
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `FRONTEND_URL` to the real domains
- a new random value for `SECRET_KEY` and a strong `DJANGO_SUPERUSER_PASSWORD`.
  The values of the template are only meant for development. Generate a random
  value with (no local Python needed):

```bash
docker compose run --rm --no-deps --entrypoint python web -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Project layout

```
core/          Project configuration and root URLs
app_auth/      Registration, activation, login, logout, token refresh, password reset
app_video/     Videos, HLS conversion and streaming
```

Both apps have a `tests/` package with the automated tests (see
[Tests](#tests)).

Each app keeps its API layer in a subpackage (`api/`) holding the serializers,
views and URLs. The business logic lives in `services.py`; the views only
validate the input and call it. Work that runs in the RQ worker lives in
`tasks.py`.

```
app_auth/
  api/cookies.py        Sets and deletes the auth cookies
  authentication.py     Reads the access token from the cookie
  tokens.py             One-time token for the activation link
  services.py           Registration, activation, password reset
  tasks.py              Renders and sends the emails, attaches the logo
  templates/emails/     MJML sources, compiled HTML and plain text of the emails
  static/app_auth/      Logo of the emails

app_video/
  services.py           ffmpeg calls, HLS paths, file cleanup
  tasks.py              Conversion job of the RQ worker
  signals.py            Starts the conversion after an upload, deletes files
  admin.py              Upload of videos
```

`core/settings_test.py` runs the tests without PostgreSQL and Redis, see
[Tests](#tests).

Other files in the root: `docker-compose.yml` (services `db`, `redis` and
`web`), `backend.Dockerfile`, `backend.entrypoint.sh` (waits for the database,
runs `collectstatic` and the migrations, creates the superuser and starts the RQ
worker and gunicorn), `.env.template` and `package.json` (builds the email
templates, see [Emails](#emails)).

---

## How a video is processed

Saving a new video in the admin panel enqueues a job for the RQ worker. The
request returns right away; the worker then runs these steps:

1. ffmpeg converts the video file into HLS, once per resolution: `480p`, `720p`
   and `1080p`. Each resolution gets a playlist `index.m3u8` and segments of 10
   seconds (`000.ts`, `001.ts`, ...) under `media/hls/<video id>/<resolution>/`.
2. If no thumbnail was uploaded, ffmpeg saves the frame at second 1 as
   `media/thumbnails/video_<id>.jpg`.

The video appears in `GET /api/video/` right after saving; its playlists answer
`404` until the conversion of that resolution is done. Depending on the length of
the video this takes from seconds to several minutes. A job is stopped after 900
seconds (`DEFAULT_TIMEOUT` in `RQ_QUEUES`).

Deleting a video removes the video file, the thumbnail and all HLS files.

---

## Emails

Two emails are sent, both through the RQ worker, so the request does not wait
for the SMTP server:

| Email          | Sent by                     | Subject               | Template         | Context                   |
| -------------- | --------------------------- | --------------------- | ---------------- | ------------------------- |
| Activation     | `POST /api/register/`       | Confirm your email    | `activation`     | `email`, `activation_url` |
| Password reset | `POST /api/password_reset/` | Reset your password   | `password_reset` | `email`, `reset_url`      |

Each email has three files: an MJML source, the compiled HTML and a plain-text
version for clients that do not show HTML:

```
app_auth/templates/emails/
  mjml/
    partials/head.mjml    Shared fonts, colors and default attributes
    activation.mjml
    password_reset.mjml
  html/                   Compiled output that Django renders, do not edit
  text/                   Plain-text part of each email (*.txt)
app_auth/static/app_auth/emails/
  logo.png                Logo used in the emails (logo.svg is the source)
```

### MJML templates

[MJML](https://mjml.io/) is a markup language for responsive emails. It compiles
to the table-based HTML with inline styles that mail clients like Outlook and
Gmail need. Only edit the `.mjml` files; the files in `html/` are overwritten
on every build.

How the templates are built:

- **Shared head** — fonts, colors and default attributes (`mj-attributes`) are
  defined once in `partials/head.mjml` and pulled into every email with
  `<mj-include>`. Change the button color there, not in the single emails.
  Partials are not compiled on their own.
- **Title and preview** — every email sets `<mj-title>` and `<mj-preview>`, the
  short text that inboxes show next to the subject.
- **Logo** — mail clients do not render SVG and block remote images by default,
  so the logo is a PNG at double size (502×80, shown at 251×40) and is sent as an
  inline attachment. The templates reference it as `cid:videoflix-logo`;
  `app_auth/tasks.py` attaches it to every email.
- **Fallback link** — below the button, every email shows the link as text, for
  clients that block buttons.
- **Django tags** — `{{ activation_url }}` and the other context variables pass
  through MJML unchanged and are filled in by Django when the email is sent.

Building needs Node.js. Install MJML once, then compile all templates:

```bash
npm install
```

```bash
npm run build:emails
```

The build runs with strict validation and fails on invalid MJML. While editing,
`npm run watch:emails` recompiles on every save. Check the result by opening the
`.html` file in a browser (the logo only shows in a sent email, because of the
`cid:` reference).

To add an email, create `mjml/<name>.mjml` with `<mj-include
path="./partials/head.mjml" />` in its `<mj-head>`, add `text/<name>.txt`, run
the build and send it with
`django_rq.enqueue(send_templated_email, template_name="<name>", ...)`.

An activation link works once. A password reset link becomes invalid as soon as
the password is changed. Both links expire after 24 hours
(`PASSWORD_RESET_TIMEOUT`).

---

## Authentication

Login sets two cookies.

| Cookie          | Lifetime   | Purpose                                     |
| --------------- | ---------- | ------------------------------------------- |
| `access_token`  | 30 minutes | Authenticates every protected request.      |
| `refresh_token` | 14 days    | Used to get a new `access_token`.           |

Both cookies are `HttpOnly` and `SameSite=Lax`; `Secure` follows
`AUTH_COOKIE_SECURE`. The client has to send credentials with every request,
otherwise the cookies are neither stored nor sent. With `fetch` this is
`credentials: "include"`. Video players have to send them as well; with hls.js
set `xhrSetup: (xhr) => { xhr.withCredentials = true; }`.

When the access token has expired, call `POST /api/token/refresh/` and repeat the
request. `POST /api/logout/` blacklists the refresh token and deletes both
cookies.

Inactive accounts can not log in; the account has to be activated through the
link of the activation email first.

Seven endpoints work without an access token: `POST /api/register/`,
`GET /api/activate/<uidb64>/<token>/`, `POST /api/login/`, `POST /api/logout/`
and `POST /api/token/refresh/` (both need the refresh cookie),
`POST /api/password_reset/` and `POST /api/password_confirm/<uidb64>/<token>/`.
Everything else answers `401` without a valid access token.

For tools without cookie support, the access token is also accepted as
`Authorization: Bearer <token>`. Postman keeps the cookies after the login. With
curl (macOS / Linux), use a cookie file; for PowerShell see
[Try the API](#try-the-api):

```bash
curl -c cookies.txt -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "S3cure-Passw0rd!"}'

curl -b cookies.txt http://localhost:8000/api/video/
```

---

## Permissions

| Action                          | Logged-in user | Staff (admin panel) |
| ------------------------------- | -------------- | ------------------- |
| List videos                     | yes            | yes                 |
| Stream playlists and segments   | yes            | yes                 |
| Upload, change, delete videos   | no             | yes                 |
| Manage users                    | no             | yes                 |

Every logged-in user sees all videos. Videos are only managed in the admin
panel; the API has no endpoints to change them.

---

## API reference

Base URL: `http://localhost:8000/api/`

Request and response bodies are JSON, except the playlists and segments of the
streaming endpoints.

### Authentication

#### `POST /api/register/`

Creates an inactive account and sends the activation email. Public.

Request:

```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "confirmed_password": "securepassword"
}
```

Response `201`:

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com"
  },
  "token": "activation_token"
}
```

The client does not need the token; it is sent in the email as well.

`400` when the passwords differ, the email is invalid or already in use, or the
password fails Django's password validators.

#### `GET /api/activate/<uidb64>/<token>/`

Activates the account. `uidb64` is the base64-encoded user id, `token` the
activation token; both come from the link in the email. Public.

Response `200`:

```json
{ "message": "Account successfully activated." }
```

`400` with `{"message": "Activation failed."}` for an invalid, expired or
already used link.

#### `POST /api/login/`

Logs in and sets the cookies `access_token` and `refresh_token`. Public.

Request:

```json
{ "email": "user@example.com", "password": "securepassword" }
```

Response `200`:

```json
{
  "detail": "Login successful",
  "user": {
    "id": 1,
    "username": "user@example.com"
  }
}
```

`400` for wrong credentials, an unknown email or an account that is not
activated yet. The response does not tell which of them applies.

#### `POST /api/logout/`

Blacklists the refresh token and deletes both cookies. Needs the
`refresh_token` cookie. The request body is `{}`.

Response `200`:

```json
{
  "detail": "Logout successful! All tokens will be deleted. Refresh token is now invalid."
}
```

`400` when the refresh cookie is missing. An invalid refresh cookie also answers
`400`, but the cookies are deleted anyway.

#### `POST /api/token/refresh/`

Reads the `refresh_token` cookie and sets a new `access_token` cookie. The
request body is `{}`.

Response `200`:

```json
{
  "detail": "Token refreshed",
  "access": "new_access_token"
}
```

The client does not need `access`; the token is set as cookie.

`400` when the refresh cookie is missing, `401` when it is expired, invalid or
blacklisted.

#### `POST /api/password_reset/`

Sends an email with a link to set a new password. Public.

Request:

```json
{ "email": "user@example.com" }
```

Response `200`:

```json
{ "detail": "An email has been sent to reset your password." }
```

The response is the same for unknown emails, so it can not be used to find out
which emails are registered; the email is only sent if the account exists.
`400` for an invalid email.

#### `POST /api/password_confirm/<uidb64>/<token>/`

Sets the new password. `uidb64` and `token` come from the link in the email.
Public.

Request:

```json
{
  "new_password": "newsecurepassword",
  "confirm_password": "newsecurepassword"
}
```

Response `200`:

```json
{ "detail": "Your Password has been successfully reset." }
```

`400` when the passwords differ, the password fails Django's password
validators, or the link is invalid, expired or already used.

---

### Video

#### `GET /api/video/`

All videos, newest first. Not paginated.

```json
[
  {
    "id": 1,
    "created_at": "2026-10-29T12:00:00Z",
    "title": "Movie Title",
    "description": "Movie Description",
    "thumbnail_url": "http://localhost:8000/media/thumbnails/image.jpg",
    "category": "Drama"
  }
]
```

`thumbnail_url` is `null` while a video has no thumbnail yet. `401` without a
token.

#### `GET /api/video/<movie_id>/<resolution>/index.m3u8`

HLS playlist of a video in one resolution. `resolution` is `480p`, `720p` or
`1080p`.

Response `200` with `Content-Type: application/vnd.apple.mpegurl`; the body is
the playlist in M3U8 format.

`401` without a token. `404` for an unknown video or resolution, or while the
conversion of that resolution is not done yet.

#### `GET /api/video/<movie_id>/<resolution>/<segment>/`

One HLS segment, for example `000.ts`. The players request it with the name of
the playlist entry, so the URL also works without the trailing slash.

Response `200` with `Content-Type: video/MP2T`; the body is the binary segment.

`401` without a token. `404` for an unknown video, resolution or segment, and for
names that are not `.ts` files.

---

## Tests

The tests use Django's test runner and the `APITestCase` of Django REST
Framework. Run them with the stack running (`docker compose up`), because the
tests need the database container:

```bash
docker compose exec web python manage.py test
```

Django creates a separate test database for the run and deletes it afterwards,
so your data is not touched. The RQ queue is replaced in the tests: emails are
sent right away into Django's test outbox, and no video is converted. ffmpeg and
Redis are therefore not needed.

Without Docker, the tests run with SQLite and without Redis through
`core/settings_test.py` (a `.env` with `SECRET_KEY` is still needed):

```bash
python manage.py test --settings=core.settings_test
```

To run only a part, pass a module or a single test:

```bash
# One app
docker compose exec web python manage.py test app_auth

# One file
docker compose exec web python manage.py test app_video.tests.test_video_segment

# One test
docker compose exec web python manage.py test app_auth.tests.test_login.LoginTests.test_sets_http_only_token_cookies
```

| File                                      | Covers                                                                                                      |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `app_auth/tests/test_register.py`         | Registration: inactive user, response with id and token, activation email with text part and inline logo, mismatching passwords, used or invalid email, weak password |
| `app_auth/tests/test_activate.py`         | Activation: valid link, invalid token or uid, link works only once                                          |
| `app_auth/tests/test_login.py`            | Login: response, `HttpOnly` cookies, case-insensitive email, wrong password, unknown email, inactive user, expired access cookie |
| `app_auth/tests/test_logout.py`           | Logout: refresh token is blacklisted and unusable afterwards, cookies are deleted, missing or invalid cookie |
| `app_auth/tests/test_token_refresh.py`    | Token refresh: new access token and cookie, missing or invalid refresh cookie                               |
| `app_auth/tests/test_password_reset.py`   | Password reset: email with link, same response without email for unknown addresses, invalid email          |
| `app_auth/tests/test_password_confirm.py` | New password: password is changed, link works only once, mismatching passwords, invalid token               |
| `app_video/tests/test_video_list.py`      | Video list: fields, absolute thumbnail URL, order, cookie and Bearer authentication, `401`                   |
| `app_video/tests/test_video_manifest.py`  | Playlist: content and content type, `Accept` header of players, unknown video or resolution, missing file   |
| `app_video/tests/test_video_segment.py`   | Segment: content and content type, URL without trailing slash, missing segment, non-`.ts` files, path traversal |

---

## Troubleshooting

**`ImproperlyConfigured: Set the SECRET_KEY environment variable`** — the `.env`
file is missing or has no `SECRET_KEY`. See [Quick start](#quick-start).

**`exec ./backend.entrypoint.sh: no such file or directory`** — the entrypoint
was saved with Windows line endings (CRLF). `.gitattributes` keeps it at LF for
new checkouts; if your editor changed it, switch the file to `LF` (in VS Code at
the bottom right) and rebuild with `docker compose up --build`.

**The log repeats `PostgreSQL ist nicht erreichbar`, or the database rejects the
login** — check `DB_HOST=db` and `DB_PORT=5432`. After changing `DB_USER` or
`DB_PASSWORD`, the old database volume still holds the old values; reset it with
`docker compose down -v` (this deletes all data, including uploaded videos).

**`relation "app_auth_user" does not exist`** — the migrations have not run.
Run `docker compose exec web python manage.py migrate` and check the logs for
the reason they failed at start.

**`Bad Request (400)` on every request, or `DisallowedHost` in the logs** — the
hostname is not in `ALLOWED_HOSTS`. Add it, for example
`ALLOWED_HOSTS=localhost,127.0.0.1`, and restart the containers.

**`401 Unauthorized` on an endpoint that should work** — log in first; without
the cookies every protected endpoint answers `401`. The access token only lives
30 minutes, so call `POST /api/token/refresh/` or log in again. Check that the
`access_token` cookie exists in the client.

**The login works but the cookies are not sent afterwards** — with `DEBUG=False`
the cookies are `Secure` by default, and browsers only send them over HTTPS. Set
`AUTH_COOKIE_SECURE=False` for local development and restart the containers.

**The client loads but every request fails** — the origin the client is served
from is not in `CSRF_TRUSTED_ORIGINS`. The value has to match protocol, host and
port exactly (`http://127.0.0.1:5500` and `http://localhost:5500` are different
origins). The requests also have to send credentials (`credentials: "include"`
with `fetch`), otherwise the cookies are dropped.

**The login answers `400` right after the registration** — the account is not
activated yet. Open the link of the activation email, or activate it as shown in
[Try the API](#try-the-api).

**No email arrives** — the emails are sent by the RQ worker, so errors do not
show up in the API response. Check `docker compose logs web` and the failed jobs
at `http://localhost:8000/django-rq/`. Common causes: wrong `EMAIL_*` values,
`EMAIL_USE_TLS` and `EMAIL_USE_SSL` both `True`, or a provider that needs an app
password instead of the account password (for example Gmail). Look in the spam
folder as well.

**The link in the email opens a page that does not exist** — `FRONTEND_URL`,
`FRONTEND_ACTIVATION_PATH` or `FRONTEND_PASSWORD_RESET_PATH` do not match the
client. Adjust them in `.env` and restart the containers.

**The email has no design, only a short text with a link** — the templates in
`app_auth/templates/emails/html/` were not compiled yet. Run `npm install` and
`npm run build:emails` (see [MJML templates](#mjml-templates)).

**`npm run build:emails` fails with a validation error** — the build runs with
strict validation. The message names the file, line and attribute; fix the
`.mjml` source, not the generated `.html`.

**The video is listed but the playlist answers `404`** — the conversion is still
running or has failed. Follow it with `docker compose logs -f web`; failed jobs
and the ffmpeg error are shown at `http://localhost:8000/django-rq/`.

**The conversion of a long video stops with `JobTimeoutException`** — a job may
run at most 900 seconds. Raise `DEFAULT_TIMEOUT` in `RQ_QUEUES` in
`core/settings.py` and restart the containers.

**`FileNotFoundError: ... 'ffmpeg'`** — ffmpeg is missing. The Docker image
installs it; rebuild with `docker compose build --no-cache`. Outside Docker,
install ffmpeg or point `FFMPEG_BINARY` to it.

**Thumbnails answer `404`** — Django only serves `/media/` with `DEBUG=True`.
With `DEBUG=False` a web server has to serve the folder, see
[Before deploying](#before-deploying).

**`Bind for 0.0.0.0:8000 failed: port is already allocated`** — another program
uses the port. Stop it or change the left side of the port mapping in
`docker-compose.yml`, for example `"8001:8000"`.
