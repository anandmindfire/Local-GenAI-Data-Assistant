# Corporate Information Security Policy

## 1. Password and Authentication Standards
- All enterprise user accounts must use Single Sign-On (SSO) backed by hardware-based FIDO2 / WebAuthn Multi-Factor Authentication (MFA).
- Standalone service accounts must use passphrases with a minimum length of 16 characters comprising uppercase, lowercase, numbers, and symbols.
- Passwords must never be shared, written on physical media, or committed to code repositories.

## 2. Data Classification and Handling
- **Public**: Marketing materials, open-source repositories, published whitepapers.
- **Internal**: Internal wikis, team meeting notes, non-sensitive operational procedures.
- **Confidential**: Business financial metrics, customer PII, commercial contract terms.
- **Restricted**: Encryption private keys, production database credentials, source code vulnerability reports.

## 3. Remote Work & Device Security
- Company data may only be accessed from MDM-enrolled, encrypted company laptops.
- Storage volumes must be encrypted with FileVault (macOS) or BitLocker (Windows).
- Automatic lock screens are enforced after 5 minutes of inactivity.
- Public Wi-Fi networks must be routed through the enterprise corporate VPN at all times.

## 4. Incident Response & Reporting
Any suspected security incident, lost laptop, phishing attempt, or unauthorized data access must be reported immediately to `security-incident@company.local` or through the `#security-soc` Slack channel.
