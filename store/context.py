from store import models as store_models # need to import the stotre models to access the database
# from customer import models as customer_models

# This is the context processor for the store app that will be used to provide data to the templates Globally
# Its going to hold the items in the cart that when a user adds an item to the cart,
# it will be stored in the session without disappearing when a refresh is made 
def default(request): 
    category_ = store_models.Category.objects.all() # Get all categories from the database

    try: # Try to get the cart_id from the session
        cart_id = request.session['cart_id'] # If it exists, use it
        total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id).count() # Count the number of items in the cart

    except: # If it does not exist, create a new cart_id and set it in the session
        total_cart_items = 0 # if it does not exist, set the total cart items to 0
        # then you need to pass this -> total_cart_items - to the cart number area in the base.html

    # try:
    #     wishlist_count = customer_models.Wishlist.objects.filter(user=request.user)
    # except:
    #     wishlist_count = 0

    return {
        "total_cart_items": total_cart_items,
        "category_": category_,
        # "wishlist_count": wishlist_count,
    }