from scoring import compute_score

fake_row = {
    "email_subject": "Urgent action required",
    "email_body": "Your account will be blocked. Click here to verify.",
    "display_name": "IT Support",
    "email_sender": "random@gmail.com",
    "auth_spf": "fail",
    "auth_dkim": "fail",
    "is_suspicious": 1,
    "is_dangerous": 0
}

score, explanation = compute_score(fake_row)

print("Score:", score)
print("Explanation:", explanation)
