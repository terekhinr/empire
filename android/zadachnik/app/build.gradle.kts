plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ru.neverretire.zadachnik"
    compileSdk = 35

    defaultConfig {
        applicationId = "ru.neverretire.zadachnik"
        minSdk = 26
        targetSdk = 35
        versionCode = 10
        versionName = "0.3.1"
        buildConfigField("String", "BASE_URL", "\"https://neverretire.ru\"")
        buildConfigField("String", "TASKS_PATH", "\"/tasks/\"")
        buildConfigField("String", "API_PATH", "\"/tasks/api/planning\"")
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.browser:browser:1.8.0")
    implementation("androidx.webkit:webkit:1.12.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
