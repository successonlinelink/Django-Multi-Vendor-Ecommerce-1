$(document).ready(function () {

    const Toast = Swal.mixin({
        toast: true,
        position: "top",
        showConfirmButton: false,
        timer: 2000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.onmouseenter = Swal.stopTimer;
            toast.onmouseleave = Swal.resumeTimer;
        },
    });

    //* This handles the add to cart functionality
    function generateCartId() {
        // Retrieve the value of "cartId" from local storage and assign it to the variable 'ls_cartId'
        const ls_cartId = localStorage.getItem("cartId");

        // Check if the retrieved value is null (i.e., "cartId" does not exist in local storage)
        if (ls_cartId === null) {
            // Initialize an empty string variable 'cartId' to store the new cart ID
            var cartId = "";

            // Loop 10 times to generate a 10-digit random cart ID
            for (var i = 0; i < 10; i++) {
                // Generate a random number between 0 and 9, convert it to an integer, and append it to 'cartId'
                cartId += Math.floor(Math.random() * 10);
            }

            // Store the newly generated 'cartId' in local storage with the key "cartId"
            localStorage.setItem("cartId", cartId);
        }

        // Return the existing cart ID from local storage if it was found, otherwise return the newly generated 'cartId'
        return ls_cartId || cartId;
    }

    $(document).on("click", ".add_to_cart", function () {
        const button_el = $(this); // Get the button element that was clicked
        const id = button_el.attr("data-id"); // Get the product ID from the button's data attribute
        const qty = $(".quantity").val(); // Get the selected quantity from the number dropdown
        const size = $("input[name='size']:checked").val(); // Get the selected size from the radio buttons
        const color = $("input[name='color']:checked").val(); // Get the selected color from the radio buttons
        const cart_id = generateCartId(); // Generate or retrieve the cart ID from local storage

        $.ajax({ // mind you, all these oulines are for the add to cart functionality just like the ones in the views.py file
            url: "/add_to_cart/",
            data: {
                id: id,
                qty: qty,
                size: size,
                color: color,
                cart_id: cart_id,
            },

            beforeSend: function () { // Show a loading spinner in the button while the request is being processed
                button_el.html('Adding To Cart <i class="fas fa-spinner fa-spin ms-2"></i>');
            },

            success: function (response) { // Handle a successful response from the server
                console.log(response);
                Toast.fire({
                    icon: "success",
                    title: response.message,
                });
                button_el.html('Added To Cart <i class="fas fa-check-circle ms-2"></i>');
                $(".total_cart_items").text(response.total_cart_items); // Update the total number of items in the cart
                //total_cart_items -> will be added in the span class for javascript in the base.html file
            },

            error: function (xhr, status, error) { // Handle an error response from the server
                button_el.html('Add To Cart <i class="fas fa-shopping-cart ms-2"></i>');

                console.log("Error Status: " + xhr.status); // Logs the status code, e.g., 400
                console.log("Response Text: " + xhr.responseText); // Logs the actual response text (JSON string)

                // Try parsing the JSON response
                try {
                    let errorResponse = JSON.parse(xhr.responseText);
                    console.log("Error Message: " + errorResponse.error); // Logs "Missing required parameters"
                    Toast.fire({
                        icon: "error",
                        title: errorResponse.error,
                    });
                } catch (e) {
                    console.log("Could not parse JSON response");
                }

                // Optionally show an alert or display the error message in the UI
                console.log("Error: " + xhr.status + " - " + error);
            },
        });
    });
    //* Add to cart functionality ends here


    //! This handles the update cart quantity (+ and -)
    $(document).on("click", ".update_cart_qty", function () { // This event listener is triggered when an element with the class "update_cart_qty" is clicked
        const button_el = $(this);
        const update_type = button_el.attr("data-update_type"); // Get the type of update (increase or decrease) from the button's data attribute
        const product_id = button_el.attr("data-product_id"); // Get the product ID from the button's data attribute
        const item_id = button_el.attr("data-item_id"); // Get the item ID from the button's data attribute
        const cart_id = generateCartId(); // Generate or retrieve the cart ID from local storage
        var qty = $(".item-qty-" + item_id).val(); // Get the current quantity from the input field with class "item-qty-{item_id}"

        if (update_type === "increase") { // If the update type is "increase"
            $(".item-qty-" + item_id).val(parseInt(qty) + 1); // Increment the quantity by 1
            qty++; // Update the qty variable to reflect the new quantity

        } else {
            // the qunantity cannot be less than 1
            if (parseInt(qty) <= 1) { // If the current quantity is less than or equal to 1
                $(".item-qty-" + item_id).val(1); // Set the quantity to 1 - so by default, the quantity cannot be less than 1
                qty = 1; // Update the qty variable to 1

            } else { // If the current quantity is greater than 1
                $(".item-qty-" + item_id).val(parseInt(qty) - 1); // Decrement the quantity by 1 - so the quantity can be decreased once it is greater than 1
                qty--; // Update the qty variable to reflect the new quantity
            }
        }

        $.ajax({
            url: "/add_to_cart/",
            data: {
                id: product_id,
                qty: qty,
                cart_id: cart_id,
            },

            beforeSend: function () {
                button_el.html('<i class="fas fa-spinner fa-spin"></i>');
            },

            success: function (response) {
                Toast.fire({
                    icon: "success",
                    title: response.message,
                });

                if (update_type === "increase") { // If the update type is "increase", change the button text to "-"
                    button_el.html("+");

                } else {
                    button_el.html("-"); // If the update type is "decrease", change the button text to "+"
                }

                // this guy will update the cart items count and subtotal when an item is updated
                $(".item_sub_total_" + item_id).text(response.item_sub_total); // Update the subtotal for the specific item
                $(".cart_sub_total").text(response.cart_sub_total); // Update the overall cart subtotal
            },

            error: function (xhr, status, error) {
                console.log("Error Status: " + xhr.status);
                console.log("Response Text: " + xhr.responseText);
                try {
                    let errorResponse = JSON.parse(xhr.responseText);
                    console.log("Error Message: " + errorResponse.error);
                    alert(errorResponse.error);
                } catch (e) {
                    console.log("Could not parse JSON response");
                }
                console.log("Error: " + xhr.status + " - " + error);
            },
        });
    });
    //* The update cart quantity functionality ends here


    //! Delete functionality for the cart items
    $(document).on("click", ".delete_cart_item", function () { // This event listener is triggered when an element with the class "delete_cart_item" is clicked
        const button_el = $(this); // Get the button element that was clicked
        const item_id = button_el.attr("data-item_id"); // Get the item ID from the button's data attribute
        const product_id = button_el.attr("data-product_id"); // Get the product ID from the button's data attribute
        const cart_id = generateCartId(); // Generate or retrieve the cart ID from local storage

        $.ajax({ // This AJAX request is sent to the server to delete the cart item
            url: "/delete_cart_item/",
            data: {
                id: product_id,
                item_id: item_id,
                cart_id: cart_id,
            },

            beforeSend: function () {
                button_el.html('<i class="fas fa-spinner fa-spin"></i>');
            },

            success: function (response) {
                Toast.fire({
                    icon: "success",
                    title: response.message,
                });
                // this guy will update the cart items count and subtotal when an item is deleted this -> 
                $(".total_cart_items").text(response.total_cart_items); // Update the total number of items in the cart
                $(".cart_sub_total").text(response.cart_sub_total); // Update the overall cart subtotal
                $(".item_div_" + item_id).addClass("d-none"); // Hide the item div for the deleted item
                // once you delete an item, the item div will be hidden
            },

            error: function (xhr, status, error) { // Handle an error response from the server
                console.log("Error Status: " + xhr.status);
                console.log("Response Text: " + xhr.responseText);
                try { // Try parsing the JSON response
                    let errorResponse = JSON.parse(xhr.responseText);
                    console.log("Error Message: " + errorResponse.error);
                    alert(errorResponse.error);
                } catch (e) {
                    console.log("Could not parse JSON response");
                }
                console.log("Error: " + xhr.status + " - " + error);
            },
        });
    });
    //* Delete functionality for the cart items ends here
    

    const fetchCountry = () => {
        fetch("https://api.ipregistry.co/?key=tryout")
            .then(function (response) {
                return response.json();
            })
            .then(function (payload) {
                console.log(payload.location.country.name + ", " + payload.location.city);
            });
    };
    fetchCountry();


    //! Filters
    // 
    $(document).on("change", ".search-filter, .category-filter, .rating-filter, input[name='price-filter'], input[name='items-display'], .size-filter, .colors-filter", function () {
        let filters = {
            categories: [],
            rating: [],
            colors: [],
            sizes: [],
            prices: "",
            display: "",
            searchFilter: "",
        };

        $(".category-filter:checked").each(function () {
            filters.categories.push($(this).val());
        });

        $(".rating-filter:checked").each(function () {
            filters.rating.push($(this).val());
        });

        $(".size-filter:checked").each(function () {
            filters.sizes.push($(this).val());
        });

        $(".colors-filter:checked").each(function () {
            filters.colors.push($(this).val());
        });

        filters.display = $("input[name='items-display']:checked").val();
        filters.prices = $("input[name='price-filter']:checked").val();
        filters.searchFilter = $("input[name='search-filter']").val();

        console.log(filters);

        $.ajax({
            url: "/filter_products/",
            method: "GET",
            data: filters,
            success: function (response) {
                // Replace product list with the filtered products
                $("#products-list").html(response.html);
                $(".product_count").html(response.product_count);
            },
            error: function (error) {
                console.log("Error fetching filtered products:", error);
            },
        });
    });

    $(document).on("click", ".reset_shop_filter_btn", function () {
        let filters = {
            categories: [],
            rating: [],
            colors: [],
            sizes: [],
            prices: "",
            display: "",
            searchFilter: "",
        };

        $(".category-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $(".rating-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $(".size-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $(".colors-filter:checked").each(function () {
            $(this).prop("checked", false);
        });

        $("input[name='items-display']").each(function () {
            $(this).prop("checked", false);
        });

        $("input[name='price-filter']").each(function () {
            $(this).prop("checked", false);
        });

        $("input[name='search-filter']").val("");

        Toast.fire({ icon: "success", title: "Filter Reset Successfully" });

        $.ajax({
            url: "/filter_products/",
            method: "GET",
            data: filters,
            success: function (response) {
                // Replace product list with the filtered products
                $("#products-list").html(response.html);
                $(".product_count").html(response.product_count);
            },
            error: function (error) {
                console.log("Error fetching filtered products:", error);
            },
        });
    });
    

    // Add to Wishlist functionality
    // This function handles the addition of products to the user's wishlist
    // It sends an AJAX request to the server with the product ID and updates the button state
    $(document).on("click", ".add_to_wishlist", function () {
        const button = $(this); // Get the button element that was clicked
        const product_id = button.attr("data-product_id"); // Get the product ID from the button's data attribute
        console.log(product_id); // Log the product ID to the console for debugging

        $.ajax({
            url: `/customer/add_to_wishlist/${product_id}/`, // Send a GET request to the server with the product ID
            beforeSend: function () {
                button.html("<i class='fas fa-spinner fa-spin text-gray'></i>"); 
            },
            success: function (response) {
                button.html("<i class='fas fa-heart text-danger'></i>");
                console.log(response);
                if (response.message === "User is not logged in") { // If the user is not logged in, show a warning message
                    button.html("<i class='fas fa-heart text-gray'></i>"); // the button will be gray by deafult

                    Toast.fire({
                        icon: "warning",
                        title: response.message,
                    });
                } else {
                    button.html("<i class='fas fa-heart text-danger'></i>"); // If the user is logged in, change the button icon to indicate that the product has been added to the wishlist
                    Toast.fire({
                        icon: "success",
                        title: response.message,
                    });
                }
            },
            error: function(){
                button.html("<i class='fas fa-heart text-danger'></i>");
            }
        });
    });

});
