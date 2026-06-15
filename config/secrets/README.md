# Build secrets (gitignored)

Credentials used **only at image build time**, mounted via BuildKit secrets to
a tmpfs during the relevant `RUN` — never written to an image layer or the
build cache. Drop the files below here; everything except this README and
`.gitkeep` is gitignored. Empty/absent → public builds with no auth.

## `netrc` — pip / torch index auth

Used by the Python service builds and `db-init`. pip reads it as `~/.netrc`:

```
machine repo.artifactory-gogent.group.echonet
login YOUR_USER
password YOUR_PASSWORD_OR_API_TOKEN
```

One `machine` line per index host. If your torch index is a different host,
add a second block.

**This is the secure home for pip/torch credentials — not the index URL.**
`PIP_INDEX_URL` / `TORCH_INDEX_URL` in `config/make.local.mk` must stay
credential-free (`https://host/.../simple`, no `user:pass@`): those URLs are
passed to the build as `--build-arg` and would leak into the image's
`docker history`. pip reads this `netrc` (mounted to `/root/.netrc` on a tmpfs
for the install `RUN` only) and authenticates to the matching host
automatically, so the URL never needs the credentials.

## `npmrc` — npm registry auth

Used by the `ui-webapp` build. npm reads it as `~/.npmrc`; use the **scoped**
form (modern npm ignores the legacy unscoped `_auth=`). The lines that
`npm login` writes are correct — copy them here:

```
//repo.artifactory-gogent.group.echonet/artifactory/api/npm/npm/:_auth=BASE64_OF_USER_PASSWORD
//repo.artifactory-gogent.group.echonet/artifactory/api/npm/npm/:always-auth=true
```

(`:_authToken=...` instead of `:_auth=...` if Artifactory issued a token.) The
scope must match `NPM_REGISTRY`'s host+path exactly, trailing slash included.
