# SAML 2.0

SAML (Security Assertion Markup Language) 2.0 is an XML-based protocol for exchanging authentication and authorization information between an Identity Provider (IdP) and a Service Provider (SP). It was standardized by OASIS in 2005 and remains the dominant enterprise SSO protocol, used by Okta, Microsoft Entra ID (formerly Azure AD), Google Workspace, and Shibboleth. This page covers the protocol's three roles, the XML message formats, the Web Browser SSO profile, and the security considerations that have driven adoption of OIDC as a modern alternative.

## The Three Roles

```text
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   User      │ ←─────→ │ Service Prov │ ←─────→ │ Identity     │
│   (browser) │         │   (SP)        │         │ Provider     │
│             │         │   e.g., SaaS │         │   (IdP)      │
│             │         │   app        │         │   e.g., Okta │
└─────────────┘         └──────────────┘         └──────────────┘
```

- **Principal**: the user, typically through a web browser.
- **Service Provider (SP)**: the application the user wants to access. The SP trusts the IdP's assertions.
- **Identity Provider (IdP)**: the system that authenticates the user and issues assertions about them.

The SP and IdP have a pre-established trust relationship (typically via X.509 certificates exchanged out-of-band). When the SP receives an assertion signed by the IdP's private key, it verifies the signature with the IdP's public key and trusts the contents.

## The SAML Assertion

A SAML assertion is an XML document signed by the IdP. It contains three parts:

```xml
<saml:Assertion xmlns:saml="..." ID="_abc123" IssueInstant="2026-08-21T...">
  <saml:Issuer>https://idp.example.com</saml:Issuer>
  <ds:Signature xmlns:ds="...">
    <!-- XML digital signature of the assertion -->
  </ds:Signature>
  <saml:Subject>
    <saml:NameID Format="...">alice@example.com</saml:NameID>
    <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
      <saml:SubjectConfirmationData
        NotOnOrAfter="2026-08-21T12:05:00Z"
        Recipient="https://sp.example.com/saml/acs"
        InResponseTo="_def456"/>
    </saml:SubjectConfirmation>
  </saml:Subject>
  <saml:Conditions
    NotBefore="2026-08-21T12:00:00Z"
    NotOnOrAfter="2026-08-21T12:05:00Z">
    <saml:AudienceRestriction>
      <saml:Audience>https://sp.example.com</saml:Audience>
    </saml:AudienceRestriction>
  </saml:Conditions>
  <saml:AuthnStatement
    AuthnInstant="2026-08-21T12:00:00Z"
    SessionIndex="_xyz789">
    <saml:SubjectLocality Address="10.0.0.5"/>
    <saml:AuthnContext>
      <saml:AuthnContextClassRef>
        urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
      </saml:AuthnContextClassRef>
    </saml:AuthnContext>
  </saml:AuthnStatement>
  <saml:AttributeStatement>
    <saml:Attribute Name="email" NameFormat="...">
      <saml:AttributeValue>alice@example.com</saml:AttributeValue>
    </saml:Attribute>
    <saml:Attribute Name="groups">
      <saml:AttributeValue>engineering</saml:AttributeValue>
      <saml:AttributeValue>admins</saml:AttributeValue>
    </saml:Attribute>
  </saml:AttributeStatement>
</saml:Assertion>
```

The assertion contains:
- **Issuer**: who issued the assertion (the IdP's URL).
- **Signature**: XML digital signature covering the entire assertion.
- **Subject**: the user's identity and how they authenticated (NameID, confirmation method).
- **Conditions**: validity window (NotBefore/NotOnOrAfter) and intended audience.
- **AuthnStatement**: when and how the user authenticated.
- **AttributeStatement**: claims about the user (email, groups, roles).

## The Web Browser SSO Profile

The most common SAML flow is the "Web Browser SSO" profile, with the SP initiating authentication:

```text
1. User → SP: GET https://sp.example.com/dashboard
   SP detects no session, generates SAML AuthnRequest.

2. SP → User: HTTP 302 to https://idp.example.com/sso
   Query string: SAMLRequest=<base64-encoded-AuthnRequest>
                  RelayState=https://sp.example.com/dashboard

3. User → IdP: GET /sso?SAMLRequest=...
   IdP checks session cookie. If absent, prompts for login.

4. User authenticates to IdP (password, MFA).

5. IdP generates SAML Assertion, signs it, embeds in SAMLResponse.

6. IdP → User: HTTP POST form to https://sp.example.com/saml/acs
   Form fields: SAMLResponse=<base64-encoded-Assertion>
                RelayState=https://sp.example.com/dashboard

7. User → SP: POST /saml/acs with SAMLResponse
   SP verifies signature, extracts NameID, creates session.

8. SP → User: HTTP 302 to RelayState URL
```

The flow involves the browser between SP and IdP, with the SP and IdP never directly communicating. The trust is established via the assertion's digital signature.

## AuthnRequest Example

```xml
<samlp:AuthnRequest xmlns:samlp="..."
  ID="_def456"
  Version="2.0"
  IssueInstant="2026-08-21T12:00:00Z"
  Destination="https://idp.example.com/sso"
  ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
  AssertionConsumerServiceURL="https://sp.example.com/saml/acs">
  <saml:Issuer>https://sp.example.com</saml:Issuer>
  <samlp:NameIDPolicy AllowCreate="true" Format="..."/>
</samlp:AuthnRequest>
```

The `ID` is a per-request identifier (used to correlate the response). `Destination` is the IdP's URL. `AssertionConsumerServiceURL` is where the SP wants the assertion sent.

## SAML Bindings

The "binding" determines how SAML messages are transported:

- **HTTP-Redirect**: the message is in the URL query string (URL-encoded, base64-encoded XML). Used for short messages (AuthnRequest).
- **HTTP-POST**: the message is in a form field submitted via POST. Used for longer messages (SAMLResponse with assertions).
- **HTTP-Artifact**: a small "artifact" (a reference) is sent via redirect or POST; the receiver fetches the full message via a back-channel SOAP call. Used when the message is too long for URL or POST.
- **SOAP**: back-channel SOAP for attribute queries or artifact resolution.

The Web Browser SSO profile typically uses HTTP-Redirect for the AuthnRequest (sent via 302) and HTTP-POST for the SAMLResponse (sent via a self-submitting form).

## SAML vs OIDC

| Aspect | SAML 2.0 | OIDC |
|--------|----------|------|
| Encoding | XML | JSON |
| Signature | XML DSig | JWS |
| Transport | HTTP-Redirect/POST | HTTP-Redirect/POST (Authorization Code flow) |
| Tokens | Assertion (per-session, long-lived) | ID Token (short) + Access Token + Refresh Token |
| API auth | Awkward (SAMLBearer) | Designed for it (Bearer tokens) |
| Modern tooling | XML-heavy, slow JSON libraries | JSON-native |
| Browser SSO | Strong (designed for it) | Strong (Authorization Code + PKCE) |
| Mobile apps | Awkward | Better (Authorization Code + PKCE) |

SAML's strengths:
- Mature, widely-deployed in enterprise (Okta, ADFS, Shibboleth).
- IdP-initiated SSO (user starts at the IdP, picks an app).

SAML's weaknesses:
- XML is heavy and slow to parse.
- XML Signature verification is error-prone (canonicalization, X.509 cert path validation).
- No standard for non-browser flows (mobile apps, IoT, API auth).
- The XML Signature Wrapping attack class has affected many SAML implementations.

## XML Signature Wrapping Attacks

A class of attacks where the attacker modifies the XML structure around a signature without invalidating the signature, trickling a parser to read a different element than what was signed:

```xml
<!-- Original (signed) -->
<Response>
  <Assertion ID="signed1">
    <Subject>alice</Subject>
    <ds:Signature>...</ds:Signature>
  </Assertion>
</Response>

<!-- Attacked (signature still valid, but a parser sees evilSubject) -->
<Response>
  <Assertion ID="signed1">
    <Subject>alice</Subject>
    <ds:Signature>...</ds:Signature>
  </Assertion>
  <Assertion ID="evil">
    <Subject>mallory</Subject>  <!-- attacker-controlled -->
  </Assertion>
</Response>
```

A naive parser (e.g., XPath `//Subject[1]`) reads the evil subject. A signature-aware parser verifies the signature on the original assertion but extracts the subject from the wrong one.

Defenses:
- Use `ID`-based lookups (`assertion = Response[ID='signed1']` rather than `//Assertion[1]`).
- Verify the signature's reference URI points to the same assertion you extracted the data from.
- Use modern SAML libraries that handle this correctly (e.g., the OneLogin Python library since 2017).

The XML Signature Wrapping attack class was identified in 2012 and has affected many production SAML deployments. The defense is in the verifier's code, not in the protocol.

## Production Deployment

IdPs in production:
- **Okta**: cloud-hosted, common for SaaS apps.
- **Microsoft Entra ID**: Microsoft's cloud IdP (formerly Azure AD).
- **Google Workspace**: cloud-hosted, common for Google ecosystem.
- **Shibboleth**: open-source IdP, common in higher education.

SPs integrate via libraries:
- **Python**: `python-saml` (OneLogin), `pysaml2`.
- **Java**: `OpenSAML`, `Spring Security SAML`.
- **Ruby**: `devise_saml_authenticatable`.
- **PHP**: `php-saml` (OneLogin).

Each library handles the XML Signature Wrapping defense, signature verification, and conditions checks. Always use a maintained library — hand-rolled SAML parsing is virtually always vulnerable.

## Common Pitfalls

1. **Forgetting to check `NotOnOrAfter`.** An assertion past its validity window should be rejected. Default windows are 5 minutes; clock skew between SP and IdP must be within this window.

2. **Not checking `AudienceRestriction`.** An assertion meant for `sp.example.com` should not be accepted by `other-sp.example.com`. Always verify the audience matches your SP's entity ID.

3. **Allowing `InResponseTo` to be missing or unverified.** An unsolicited assertion (no `InResponseTo`) is allowed for IdP-initiated SSO but should be a configuration choice, not the default.

4. **Trusting the assertion's signature without verifying the signing cert is trusted.** The signing cert must be the IdP's known cert (exchanged out-of-band). A self-signed cert from an attacker should not be trusted.

5. **Long-lived SP sessions.** SAML assertions expire after ~5 minutes, but SP sessions often last hours or days. The SP should re-check authorization (e.g., for group membership changes) periodically, not just on the initial SAML login.

6. **Replay attacks across SPs.** A captured assertion can be replayed against a different SP if the second SP accepts the same IdP's assertions. The `AudienceRestriction` field prevents this — always set it.

## References

- [OASIS SAML 2.0 specification](https://www.oasis-open.org/standardssaml/) (2005)
- [SAML Wikipedia](https://en.wikipedia.org/wiki/SAML_2.0)
- [Okta SAML documentation](https://developer.okta.com/docs/concepts/saml/)
- [Shibboleth IdP documentation](https://shibboleth.atlassian.net/wiki/spaces/IDP5/overview)
- [OneLogin python-saml](https://github.com/onelogin/python-saml)
- [OpenSAML Java library](https://wiki.shibboleth.net/confluence/display/OpenSAML/Home)
- [SAML XML Signature Wrapping attacks (2012)](https://www.usenix.org/system/files/conference/usenixsecurity12/sec12-final91.pdf)
- [Spring Security SAML](https://docs.spring.io/spring-security/reference/saml2/index.html)
