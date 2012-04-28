casper = require('casper').create verbose: true, logLevel: 'debug'

casper.start 'http://localhost:8000/login/google', ->
    @log "Go to /login/google on authauth view to authicate using Google.", "debug"
    @capture "test_view_output/01_login_google.png"

    # -----------------------------------------------------------------------
    #  Validate assumptions.
    # -----------------------------------------------------------------------
    @test.assertTitle "Google Accounts", "Google sign-in page title is what we expect."
    @test.assertExists "form#gaia_loginform", "There is a form on the page."
    @test.assertExists "input#Email", "There is an email element."
    @test.assertExists "input#Passwd", "There is a password element."
    @test.assertExists "input#signIn", "There is a sign-in button element."
    @test.assertExists "input#PersistentCookie", "There is a persistent cookie element."
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    #  Fill in the form, then submit.
    # -----------------------------------------------------------------------
    @wait 3000, ->
        @click "input#PersistentCookie"
        @fill "form#gaia_loginform", { "Email":  "iamatestuser@asimihsan.com", "Passwd": "xxxxxxxxxx" }, true
    # @capture "test_view_output/02_login_google_form_filled.png"
    # @click "input#signIn"
    # -----------------------------------------------------------------------

casper.then ->
    @wait 10000, ->
        @log "Tell Google that we want to permit this application to access our data", "debug"
        @capture "test_view_output/03_login_google_before_permit.png"
        @log "Current URI: #{ @getCurrentUrl() }"
        @waitForSelector "input#approve_button",
            ->
                @capture "test_view_output/04_login_google_after_permit.png"
                @click "input#approve_button",
            ->
                @die "approve_button didn't show up in time.",
                10000 

casper.then ->
    @log "We should get redirected to the successful authentication URI."
    @capture "test_view_output/05_login_google_before_final_page.png"
    @wait 3000
    @log "Current URI: #{ @getCurrentUrl() }"
    @capture "test_view_output/06_log_google_after_final_page.png"

casper.run()

