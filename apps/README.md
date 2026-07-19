# Apps

`apps/` contains repository-local developer tools that support PersonaBench but
are not one of the three contribution modules.

Current apps:

- `viewer/`: React frontend source for `harbor view`. The backend lives in
  `environment/runtime/harbor/viewer/`, and built static files are generated
  under `environment/runtime/harbor/viewer/static/` when needed.

Do not put generated builds, job outputs, datasets, or module-owned business
logic here.
