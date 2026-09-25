# Publishing to nuget.org with trusted publishing

Adapted from dotnet/skills `plugins/dotnet-advanced/skills/nuget-trusted-publishing` and its
`references/publish-workflow.md` (MIT, © .NET Foundation and Contributors). Changes: condensed; version check
made a required gate; pack-inspection and package-validation steps added.

Trusted publishing replaces a long-lived nuget.org API key with a short-lived token obtained through GitHub's
OIDC identity. There is no secret to leak or rotate. It applies to nuget.org only (not Azure Artifacts or private
feeds) and to GitHub Actions.

## 1. Before the first publish

A pushed version is permanent: it can be unlisted, never replaced. Verify locally first.

1. **Classify each packable project:** library, `PackAsTool` (dotnet tool), `PackageType=McpServer`,
   `PackageType=Template`. Check `Directory.Build.props` too; package metadata is often set there.
2. **Required metadata:** `PackageId`, `Version`, `Authors`, `Description`, `PackageLicenseExpression`,
   `RepositoryUrl`, `PackageReadmeFile`. Turn on `EnablePackageValidation` (API compatibility against the previous
   version) and deterministic, SourceLink-enabled builds (`ContinuousIntegrationBuild=true` in CI).
3. **Pack and inspect:** `dotnet pack -c Release -o ./artifacts`, then open the `.nupkg` (it's a zip) and check
   the TFM folder, the README, the license, and that no test, sample or local-path file slipped in. For a tool,
   `dotnet tool install --add-source ./artifacts`, run it, uninstall it.
4. **For MCP servers**, the version in `.mcp/server.json` (root and `packages[]`) must equal the project version.

## 2. The nuget.org policy (a human does this)

At nuget.org → account → Trusted Publishing → Add policy:

- **Repository owner** and **repository**: the GitHub owner and repo.
- **Workflow file**: the exact filename (`publish.yml`), no path, not the workflow's `name:`.
- **Environment**: only if the job declares `environment:`; must match it.

The policy's owner (a user or an organization) must own the package ID. A policy for a private repository is
temporary for 7 days until the first successful publish. Wait for the owner to confirm the policy exists before
running the workflow or removing any old API key.

## 3. The workflow

Keep CI (build and test on every push and PR) separate from publishing (tag-triggered, needs `id-token: write`).

```yaml
name: Publish to NuGet
on:
  push:
    tags: ['v*']

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: release              # secret scoping + optional required reviewers
    permissions:
      id-token: write                 # required: NuGet/login fails with 403 without it
      contents: read                  # setting permissions replaces the defaults
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          global-json-file: global.json   # the SDK the repo pins, not a second copy of it
      - name: Tag must equal project version
        run: |
          tag="${GITHUB_REF_NAME#v}"
          ver=$(dotnet msbuild src/MyLib/MyLib.csproj -getProperty:Version)
          [ "$tag" = "$ver" ] || { echo "::error::tag $tag != project version $ver"; exit 1; }
      - run: dotnet test -c Release     # the published bits pass the gate, from this commit
      - run: dotnet pack src/MyLib/MyLib.csproj -c Release -o ./artifacts
      - name: NuGet login (OIDC)
        id: login
        uses: NuGet/login@v1
        with:
          user: ${{ secrets.NUGET_USER }} # nuget.org profile name, not the email address
      - run: >
          dotnet nuget push ./artifacts/*.nupkg
          --api-key ${{ steps.login.outputs.NUGET_API_KEY }}
          --source https://api.nuget.org/v3/index.json --skip-duplicate
```

- `dotnet msbuild -getProperty:Version` reads the evaluated version wherever it is set; don't `sed` the csproj.
- Keep `NuGet/login` close to the push: the token expires in about an hour.
- Pin third-party actions to a commit SHA.
- Migrating from an API key: add `id-token: write`, the environment and the login step, replace the key in the push
  step, publish once successfully, **then** delete the old secret and revoke the key on nuget.org.

## 4. Troubleshooting

| Symptom | Cause |
|---|---|
| `NuGet/login` 403 | `id-token: write` missing from the job's permissions |
| "no matching policy" | workflow filename, repo, owner or environment differs from the policy |
| push unauthorized | the policy's owner doesn't own this package ID |
| token expired | too long between login and push |
| `already exists` | re-running the same version; `--skip-duplicate` keeps re-runs idempotent |
| a re-run uses the old YAML | `gh run rerun` replays the workflow from the tagged commit; fix forward with a new version, never re-tag a published version |

If an infrastructure or auth failure survives one fix attempt, stop and ask the owner. Never delete tags,
releases, secrets or package versions without confirmation.
