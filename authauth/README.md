Introduction
------------

authauth is the component responsible for authenticating and authorising users. Over ZeroMQ it will answer such questions as:

-   Authentication
    -   Create
        -   Could you please create an internal user the corrsponds to the following Google / Facebook / Twitter / BrowserID user?
    -   Read
        -   An HTTP client has given me the following cookie. Could you please tell me if this is a valid cookie? Valid is defined as the result of a server secret and an HMAC such that only you could have possible given out this cookie. If so, what internal user ID does this cookie correspond to?
        -   Do you know a Google / Facebook / Twitter / BrowserID user with this ID? If so, what is their internal user ID?
        -   I think the following internal user ID should be allowed to log in. Could you please make a note of this, and generate a cookie for them to use?
    -   Update
        -   Could you please associate the following Google / Facebook / Twitter / BrowserID credential with the following internal user ID?
    -   Delete
        -   Could you please remove the authorisation for the following internal user ID?

-   Authorisation
    -   What is the following internal user ID permitted to do?
    -   Is the following internal user ID permitted to execute the following function with these associated arguments?

How to execute the tests
------------------------

-   In the root of this directory execute the following to use nose to execute all tests when any Python files are modified:

```shell
watchmedo shell-command --patterns="*.py" --recursive --command="clear; date; nosetests --no-skip --detailed-errors --stop --verbosity=2 --tests=test/"
```

