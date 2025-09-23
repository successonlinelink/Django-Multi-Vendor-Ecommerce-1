from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout

from userauths import models as userauths_models
from userauths import forms as userauths_forms
from vendor import models as vendor_models


# Register Functionality
def register_view(request):
    if request.user.is_authenticated:
        messages.warning(request, f"You are already logged in")
        return redirect('/')   

    form = userauths_forms.UserRegisterForm(request.POST or None) # if registration is submitted, post it, but if form is empty, don't post anything

    if form.is_valid():
        user = form.save()

        full_name = form.cleaned_data.get('full_name')
        email = form.cleaned_data.get('email')
        mobile = form.cleaned_data.get('mobile')
        password = form.cleaned_data.get('password1')
        user_type = form.cleaned_data.get("user_type")

        # After registration, you can log the user in automatically
        user = authenticate(email=email, password=password)
        login(request, user)

        messages.success(request, f"Account was created successfully.")
        profile = userauths_models.Profile.objects.create(full_name = full_name, mobile = mobile, user=user)
        
        if user_type == "Vendor": # if the user selects vendor, create a vendor profile
            vendor_models.Vendor.objects.create(user=user, store_name=full_name) # use the name as the store name - store is coming from the vendor class in the vendor model
            profile.user_type = "Vendor" # then the type of account will be vendor account
        else:
            profile.user_type = "Customer" # if the user selects customer, create a customer profile
        
        profile.save()

        # if maybe they added to cart and want to pay before being logged in or registered, we want to redirect them to the cart page after registration or logged in for them to finish the payment rather than redirecting them to the index page
        next_url = request.GET.get("next", 'store:index') # get the next url from the request, if it does not exist, redirect to store:index
        return redirect(next_url) # 
    
    context = {
        'form':form
    }
    return render(request, 'userauths/sign-up.html', context)


# Login Functionality
def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in")
        return redirect('store:index')
    
    if request.method == 'POST':
        form = userauths_forms.LoginForm(request.POST)  
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # captcha_verified = form.cleaned_data.get('captcha', False)  

            # if captcha_verified:
            try: # if email is active and password and email match, 
                user_instance = userauths_models.User.objects.get(email=email, is_active=True)
                user_authenticate = authenticate(request, email=email, password=password)

                if user_instance is not None: # and the both detail exist in the database
                    login(request, user_authenticate) # log them in
                    messages.success(request, "You are Logged In")
                    next_url = request.GET.get("next", 'store:index') # take them to the path where they were before loggin

                    
                    if next_url == '/undefined/': # if he was not trying to access any page and just came to login page directly, but if he was trying to access a page, then redirect him to that page after login
                        return redirect('store:index') # else, return him to the index page
                    
                    # if next_url == 'undefined': #
                    #     return redirect('store:index')

                    if next_url is None or not next_url.startswith('/'): # Ensures the next_url begins with / (meaning it’s a relative path within your site) else
                        return redirect('store:index') # else, return him to the index page

                    return redirect(next_url)

                else:
                    messages.error(request, 'Username or password does not exist')
                    
            except userauths_models.User.DoesNotExist:
                messages.error(request, 'User does not exist')
                
            # else:
            #     messages.error(request, 'Captcha verification failed. Please try again.')

    else:
        form = userauths_forms.LoginForm()  

    return render(request, "userauths/sign-in.html", {'form': form})


# Logout Functionality
def logout_view(request):
    # This is to preserve the cart id in the session after logout
    if "cart_id" in request.session: # if there is a cart id in the session, store it in a variable
        cart_id = request.session['cart_id'] # get the cart id from the session
    else:
        cart_id = None # if there is no cart id in the session, set it to None
        
    logout(request)
    request.session['cart_id'] = cart_id # set the cart id in the session to the preserved cart id
    messages.success(request, 'You have been logged out.')
    return redirect("userauths:sign-in")

# def handler404(request, exception, *args, **kwargs):
#     context = {}
#     response = render(request, 'userauths/404.html', context)
#     response.status_code = 404
#     return response

# def handler500(request, *args, **kwargs):
#     context = {}
#     response = render(request, 'userauths/500.html', context)
#     response.status_code = 500
#     return response

