casper = require('casper').create verbose: true, logLevel: 'debug'

username = "iamatestuser@asimihsan.com"
password = "reds922(zest"
start_url = "http://localhost:8000/login/google"
end_url = "http://localhost:8000/login/google/successful/"
screenshot_directory = "test_view_login_google_output/"

casper.start start_url, ->
    @log "Go to /login/google on authauth view to authicate using Google.", "debug"
    casper.viewport(1024, 768)
    @capture screenshot_directory + "01_login_google.png"

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
    @fill "form#gaia_loginform", { "Email":  username, "Passwd": password }
    @evaluate ->
        document.querySelector("input#PersistentCookie").checked = false
    @wait 3000, ->
        @capture screenshot_directory + "02_login_google_form_filled.png"
        @click "input#signIn"
    # -----------------------------------------------------------------------

casper.then ->
    @waitForSelector "input#approve_button", ->
        @waitForSelector "#remember_choices_checkbox", ->
            @log "Current URI: #{ @getCurrentUrl() }"
            @capture screenshot_directory + "03_login_google_after_permit.png"
            @evaluate ->
                document.querySelector("#remember_choices_checkbox").checked = false
            @click "input#approve_button",
        ->
            @die "remember_choices_checkbox didn't show up in time.",
            10000,
    ->
        @die "approve_button didn't show up in time.",
        10000 

casper.then ->
    @log "We should get redirected to the successful authentication URI."
    @capture screenshot_directory + "05_login_google_before_final_page.png"
    @wait 10000, ->
        @capture screenshot_directory + "06_log_google_after_final_page.png"
        @log "Current URI: #{ @getCurrentUrl() }"
        @test.assertEquals(@getCurrentUrl(), end_url)

casper.run ->
    @log "test_view_login_google finished."
    this.test.renderResults true

