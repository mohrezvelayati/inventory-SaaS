# Portfolio Demo Checklist

Use synthetic names and phone numbers only.

1. Click **ورود به نسخهٔ نمایشی** and confirm the shared demo manager opens a
   populated dashboard without credentials.
2. Confirm products, variants, customers, members, pending invitations,
   inventory alerts, sales, wanted demand, and 30-day reports contain synthetic
   data.
3. Create a category and product, then add a size and initial purchase stock.
4. Create a customer and a draft sale; add an item and complete checkout.
5. Confirm stock decreased and the movement history contains the sale entry.
6. Open dashboard and reports and verify revenue, profit, and product metrics.
7. Record an unavailable product request and confirm wanted demand increments.
8. Create a seller invitation, open it in a private session, register the
   employee, and verify capability-aware navigation.
9. Log out and confirm the old refresh token cannot be reused.
10. Once SMS is enabled, complete the password reset workflow and confirm the
   previous password and tokens are rejected.
11. Check readiness, Render logs, Sentry, and the deployed backend/frontend SHAs.

After the demonstration, delete draft-only test records through supported UI/API
operations. Preserve completed sales as audit records; never delete them directly.
The guarded `seed_demo --reset` maintenance command is the sole exception and
removes only synthetic records belonging to the marked demo tenant.
