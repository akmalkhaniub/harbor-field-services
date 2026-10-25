# Safe change

1. Branch from `main`.
2. Change the rate rule in `services/rate-api/ratecard/policy.py` and update `data/policy/services-policy.md` in the same pull request.
3. Run `python -m pytest`. The eval set fails if an answer leaks another account or sends mail.
4. Import the solution to Dev only. Prod is a managed import from GitHub after the pull request is reviewed.
