package com.staunt.browser

import android.app.AlertDialog
import android.content.Context
import android.net.Uri
import android.view.View
import android.webkit.*
import android.widget.Toast

class StauntChromeClient(
    private val context: Context,
    private val onProgressChanged: (Int) -> Unit,
    private val onTitleReceived: (String) -> Unit,
    private val onFileChooser: ((ValueCallback<Array<Uri>>?, WebChromeClient.FileChooserParams?) -> Boolean)? = null
) : WebChromeClient() {

    override fun onProgressChanged(view: WebView, newProgress: Int) {
        super.onProgressChanged(view, newProgress)
        onProgressChanged(newProgress)
    }

    override fun onReceivedTitle(view: WebView, title: String) {
        super.onReceivedTitle(view, title)
        onTitleReceived(title)
    }

    // Real File Upload Dialog
    override fun onShowFileChooser(
        webView: WebView?,
        filePathCallback: ValueCallback<Array<Uri>>?,
        fileChooserParams: FileChooserParams?
    ): Boolean {
        if (onFileChooser != null) {
            return onFileChooser.invoke(filePathCallback, fileChooserParams)
        }
        return super.onShowFileChooser(webView, filePathCallback, fileChooserParams)
    }

    // Native Permission Handlers: Geolocation
    override fun onGeolocationPermissionsShowPrompt(
        origin: String?,
        callback: GeolocationPermissions.Callback?
    ) {
        AlertDialog.Builder(context)
            .setTitle("Location Permission")
            .setMessage("The website '$origin' would like to access your device location.")
            .setPositiveButton("Allow") { _, _ -> callback?.invoke(origin, true, true) }
            .setNegativeButton("Deny") { _, _ -> callback?.invoke(origin, false, false) }
            .setCancelable(false)
            .show()
    }

    // Native Permission Handlers: Camera / Microphone
    override fun onPermissionRequest(request: PermissionRequest?) {
        if (request == null) return
        val requestedResources = request.resources
        val resNames = requestedResources.joinToString(", ") { res ->
            when (res) {
                PermissionRequest.RESOURCE_VIDEO_CAPTURE -> "Camera"
                PermissionRequest.RESOURCE_AUDIO_CAPTURE -> "Microphone"
                PermissionRequest.RESOURCE_PROTECTED_MEDIA_ID -> "Protected Media"
                else -> res
            }
        }

        AlertDialog.Builder(context)
            .setTitle("Device Permission Request")
            .setMessage("The website '${request.origin}' is requesting access to: $resNames.")
            .setPositiveButton("Grant") { _, _ -> request.grant(request.resources) }
            .setNegativeButton("Deny") { _, _ -> request.deny() }
            .setCancelable(false)
            .show()
    }

    // Native JS Dialog Interception
    override fun onJsAlert(view: WebView?, url: String?, message: String?, result: JsResult?): Boolean {
        AlertDialog.Builder(context)
            .setTitle("Alert")
            .setMessage(message ?: "")
            .setPositiveButton("OK") { _, _ -> result?.confirm() }
            .setOnCancelListener { result?.cancel() }
            .show()
        return true
    }

    override fun onJsConfirm(view: WebView?, url: String?, message: String?, result: JsResult?): Boolean {
        AlertDialog.Builder(context)
            .setTitle("Confirm")
            .setMessage(message ?: "")
            .setPositiveButton("OK") { _, _ -> result?.confirm() }
            .setNegativeButton("Cancel") { _, _ -> result?.cancel() }
            .setOnCancelListener { result?.cancel() }
            .show()
        return true
    }
}
