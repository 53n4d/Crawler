import asyncio

class CrawlerHelpers:
    async def detection_cl_elements(page, elements_from_crawler, input_elements_from_crawler):
        script = """
        (function() {
            var colors = ["blue", "red", "green", "black", "orange", "yellow", "indigo", "violet", "pink", "brown", "black", "gray", "white"]; // add more colors if needed
            var levelCounts = {}; // Object to hold counts of elements at each level
            window.detected_elements = []; // Initialize detected_elements array on the window object
            window.detected_input_elements = [];

            function generateSelectorPath(element) {
                if (!element || !element.tagName) return '';
                const tagName = element.tagName.toLowerCase();
                if (['body', 'html'].includes(tagName)) return tagName;
                if (element.id) return '#' + element.id;
                if (element.style.display === 'none' || element.style.visibility === 'hidden') return '';
                if (element.parentElement.tagName.toLowerCase() === 'body') return tagName;
                const classSelector = [...element.classList].map(className => '.' + className).join('');
                if (classSelector && document.querySelectorAll(classSelector).length === 1) return classSelector;
                let selectors = [];
                while (element.parentNode) {
                    let sibling = element;
                    let nth = 1;
                    while (sibling.previousElementSibling) {
                        sibling = sibling.previousElementSibling;
                        nth++;
                    }
                    selectors.unshift(`${element.tagName.toLowerCase()}:nth-child(${nth})`);
                    if (element.parentElement.tagName.toLowerCase() === 'body' || element.id) break;
                    element = element.parentElement;
                }

                const selector = selectors.join(' > ');
                if (selector === tagName) {
                    const findChildWithClasses = (el) => {
                        for (let child of el.children) {
                            if (child.classList.length > 0) {
                                return generateSelectorPath(child);
                            } else {
                                const innerSelector = findChildWithClasses(child);
                                if (innerSelector) return innerSelector;
                            }
                        }
                        return null;
                    }

                    const childSelector = findChildWithClasses(element);
                    if (childSelector) return childSelector;
                }

                return selector;
            }

            function isVisibleInViewport(element) {
                var style = window.getComputedStyle(element);
                return style && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
            }

            function createHash(element) {
                var str = element.tagName + ':' + (element.id || "") + (element.name || "") + ':' + (element.getAttribute('href') || "") + ':' + (element.getAttribute('aria-label') || "") + ':' + (element.getAttribute('for') || "") + ':' + (element.textContent || "");
                return str.split('').reduce((hash, char) => {
                    var code = char.charCodeAt(0);
                    hash = ((hash << 5) - hash) + code;
                    return hash & hash; // Convert to 32-bit integer
                }, 0);
            }

            function isReallyClickable(element) {
                if (element.hasAttribute('data-reach-dialog-overlay')) {
                    return false;
                }
                const clickableTags = ["BUTTON", "A", "INPUT"];
                const isClickableTag = clickableTags.includes(element.tagName);
                const hasPointerCursor = window.getComputedStyle(element).cursor === 'pointer';
                return isClickableTag || hasPointerCursor;
            }

            function detectClickableWithin(level, element, parentElement, levelOrders) {
                var items = Array.prototype.slice.call(element.querySelectorAll('*')).map(function(child) {
                    var include = isReallyClickable(child);
                    return {
                        element: child,
                        include: include,
                    };
                });

                items = items.filter(x => x.include && isVisibleInViewport(x.element) && !x.element.getAttribute('detected') && !hasClickableParent(x.element, items));

                function hasClickableParent(childElement, allItems) {
                    return allItems.some(item => item.element.contains(childElement) && item.include && item.element !== childElement);
                }

                items.forEach(function(item) {
                    item.element.style.border = "3px dashed " + colors[level % colors.length];
                    item.element.setAttribute('detected', 'true');

                    var hash = createHash(item.element);
                    var href = item.element.getAttribute('href') || item.element.getAttribute('routerlink') || "";

                    var elementOrder = levelOrders[level] || 0; // Assuming level 0 for these elements
                    levelOrders[level] = elementOrder + 1;

                    var elementInfo = {
                        tagName: item.element.tagName,
                        className: item.element.className,
                        innerHTML: item.element.innerHTML,
                        level: level, // Assuming level 0 for these elements
                        href: href,
                        clicked: 'no',
                        order: elementOrder,
                        selectorPath: generateSelectorPath(item.element),
                        currentUrl: window.location.href,
                        forAttribute: item.element.getAttribute('for') || ""
                    };

                    if (parentElement) {
                        var parentHash = createHash(parentElement);
                        var parentInfo = window.detected_elements.find(function(elem) {
                            return (
                                elem.hash === parentHash
                            );
                        });
                        if (parentInfo) {
                            elementInfo.parentElement = {
                                level: parentInfo.level,
                                order: parentInfo.order,
                                hash: parentInfo.hash,
                                parentSelPath: parentInfo.selectorPath
                            };
                        }
                    }

                    var alreadyDetected = window.detected_elements.some(function(detectedElement) {
                        return detectedElement.hash === hash;
                    });

                    if (!alreadyDetected) {
                        elementInfo.hash = hash;
                        window.detected_elements.push(elementInfo);
                        highlightAndStoreInputSets(parentInfo ? parentInfo.hash : null);
                    }
                });
            }

            var levelOrders = {}; // Object to hold order for each level

            function findAndHighlightElements(level, parentElement, levelOrders) {
                var items = Array.prototype.slice.call(
                    document.querySelectorAll('*')
                ).map(function(element) {
                    var include = (element.tagName === "BUTTON" || element.tagName === "A" ||
                        (element.tagName.toLowerCase().indexOf('input') > -1 && element.type == "button") ||
                        (element.onclick != null) ||
                        window.getComputedStyle(element).cursor == "pointer") ||
                        Array.from(element.classList).some(className => className.includes('dropdown'));
                    return {
                        element: element,
                        include: include,
                    };
                });

                items = items.filter(x => x.include && isVisibleInViewport(x.element) && !x.element.getAttribute('detected') && !hasClickableParent(x.element, items));

                function hasClickableParent(element, allItems) {
                    return allItems.some(item => item.element.contains(element) && item.include && item.element !== element);
                }

                items.forEach(function(item, index) {
                    item.element.style.border = "3px dashed " + colors[level % colors.length];
                    item.element.setAttribute('detected', 'true');
                    var hash = createHash(item.element);
                    var href = item.element.getAttribute('href') || item.element.getAttribute('routerlink') || "";

                    let observer;  // Define the observer outside the click event to ensure only one instance is active

                    function inspectChildElements(element, clickedElement, level, levelOrders, colors) {
                        // Apply the border and detection logic to the current element if it's an <a> tag
                        if (element.tagName === "A") {
                            element.style.border = "3px dashed " + colors[level % colors.length];

                            // Detect and log information of the element
                            var elementHash = createHash(element);
                            var elementHref = element.getAttribute('href') || element.getAttribute('routerlink') || "";

                            var elementInfo = {
                                tagName: element.tagName,
                                className: element.className,
                                innerHTML: element.innerHTML,
                                level: level,
                                href: elementHref,
                                clicked: 'no',
                                order: levelOrders[level] || 0,
                                selectorPath: generateSelectorPath(element),
                                currentUrl: window.location.href
                            };

                            if (clickedElement) {
                                var parentHash = createHash(clickedElement);
                                var parentDetected = window.detected_elements.find(elem => elem.hash === parentHash);

                                if (parentDetected) {
                                    elementInfo.parentElement = {
                                        level: parentDetected.level,
                                        order: parentDetected.order,
                                        hash: parentDetected.hash
                                    };
                                }
                            }

                            var alreadyDetected = window.detected_elements.some(function(detectedElement) {
                                return detectedElement.hash === elementHash;
                            });

                            if (!alreadyDetected) {
                                elementInfo.hash = elementHash;
                                window.detected_elements.push(elementInfo);
                            }

                            // Update the order for the next element on the same level
                            levelOrders[level] = elementInfo.order + 1;
                        }

                        // Recursively call inspectChildElements for each child of the current element
                        Array.from(element.children).forEach(child => {
                            inspectChildElements(child, clickedElement, level + 1, levelOrders, colors);
                        });
                    }

                    item.element.addEventListener('click', async function(event) {
                        const clickedElement = event.currentTarget;  // Get the element on which the event handler was attached

                        inspectChildElements(clickedElement, clickedElement, level + 1, levelOrders, colors);

                        requestAnimationFrame(function() {
                            var detectedElement = item.element;
                            findAndHighlightElements(level + 1, detectedElement, levelOrders);
                        });
                        if (observer) {
                            observer.disconnect();
                        }
                        observer = new MutationObserver(mutations => {
                            mutations.forEach(mutation => {
                                if (mutation.addedNodes.length) {
                                    mutation.addedNodes.forEach(node => {
                                        if (node.nodeType === Node.ELEMENT_NODE) {
                                            if (node.tagName !== 'STYLE' && window.getComputedStyle(node).visibility !== 'hidden') {
                                                node.childNodes.forEach(child => {
                                                    if (child.nodeType === Node.ELEMENT_NODE) {
                                                        detectClickableWithin(level + 1, child, clickedElement, levelOrders);  // Pass the clicked element as the parent
                                                    }
                                                });
                                            }
                                        }
                                    });
                                }
                            });
                        });

                        observer.observe(document, {
                            childList: true,
                            subtree: true
                        });

                        setTimeout(() => {
                            if (observer) {
                                observer.disconnect();
                            }
                        }, 10000);
                    });

                    var elementOrder = levelOrders[level] || 0;
                    levelOrders[level] = elementOrder + 1;

                    var elementInfo = {
                        tagName: item.element.tagName,
                        className: item.element.className,
                        innerHTML: item.element.innerHTML,
                        level: level,
                        href: href,
                        clicked: 'no',
                        order: elementOrder,
                        selectorPath: generateSelectorPath(item.element), // Added selector path
                        currentUrl: window.location.href,  // Add the current URL to the element info
                        forAttribute: item.element.getAttribute('for') || ""
                    };

                    if (parentElement) {
                        parentHash = createHash(parentElement)
                        var parentInfo = window.detected_elements.find(function(elem) {
                            return (
                                elem.hash === parentHash
                            );
                        });
                        if (parentInfo) {
                            elementInfo.parentElement = {
                                level: parentInfo.level,
                                order: parentInfo.order,
                                hash: parentInfo.hash,
                                parentSelPath: parentInfo.selectorPath
                            };
                        }
                    }

                    var alreadyDetected = window.detected_elements.some(function(detectedElement) {
                        return detectedElement.hash === hash;
                    });

                    if (!alreadyDetected) {
                        elementInfo.hash = hash;
                        window.detected_elements.push(elementInfo);
                    }
                });
            }

            function createInputHash(str) {
                str = String(str);
                return str.split('').reduce((hash, char) => {
                    var code = char.charCodeAt(0);
                    hash = ((hash << 5) - hash) + code;
                    return hash & hash; // Convert to 32-bit integer
                }, 0);
            }

            function detectInputSetsWithin(element) {
                var inputs = Array.from(element.querySelectorAll('input:not([type="button"]), textarea, select, button[type="submit"], input[type="submit"]'));
                if (inputs.length === 0) return [];

                var inputSets = [];
                while (inputs.length > 0) {
                    var firstInput = inputs[0];
                    var commonAncestor = firstInput.closest('form') || firstInput.parentElement;

                    while (commonAncestor) {
                        var siblings = Array.from(commonAncestor.querySelectorAll('input:not([type="button"]), textarea, select, button[type="submit"], input[type="submit"]'));
                        if (siblings.every(input => inputs.includes(input))) break;
                        commonAncestor = commonAncestor.parentElement;
                    }
                    if (!commonAncestor) {
                        inputs = inputs.filter(input => input !== firstInput);
                        continue;
                    }
                    inputSets.push({
                        container: commonAncestor,
                        inputs: siblings
                    });

                    inputs = inputs.filter(input => !siblings.includes(input));
                }
                return inputSets;
            }

            function highlightAndStoreInputSets(parent = undefined) {
                var detectedInputSetInfos = [];
                var inputSets = detectInputSetsWithin(document.body);
                inputSets.forEach((inputSet, index) => {
                    var concatenatedInputDetails = inputSet.inputs.reduce((acc, input) => {
                        return acc + input.tagName + input.type + input.name + input.placeholder;
                    }, '');
                    fullInput = concatenatedInputDetails + inputSet.container.tagName + inputSet.container.className + window.location.href
                    var hash = createInputHash(fullInput);
                    inputSet.container.style.border = "3px dashed " + colors[(index + 1) % colors.length];
                    inputSet.container.setAttribute('detected-input-set', 'true');

                    var inputSetInfo = {
                        type: 'inputSet',
                        tagName: inputSet.container.tagName,
                        className: inputSet.container.className,
                        innerHTML: inputSet.container.innerHTML,
                        selectorPath: generateSelectorPath(inputSet.container),
                        isFilled: "no",
                        clicked: "yes",
                        href: "/",
                        currentUrl: window.location.href,
                        inputs: inputSet.inputs.map(input => ({
                            tagName: input.tagName,
                            type: input.type,
                            name: input.name,
                            value: input.value,
                            placeholder: input.placeholder,
                            id: input.id,
                            accept: input.accept,
                            selectorPath: generateSelectorPath(input)
                        }))
                    };

                    var alreadyDetected = window.detected_input_elements.some(function(detectedElement) {
                        return detectedElement.hash === hash;
                    });

                    if (!alreadyDetected) {
                        inputSetInfo.hash = hash;
                        inputSetInfo.parentHash = parent;
                        window.detected_input_elements.push(inputSetInfo);
                        detectedInputSetInfos.push(inputSetInfo);
                    }
                });
                return detectedInputSetInfos;
            }

            function scrollElementIncrementally(element, step, callback) {
                let lastScrollTop = element.scrollTop;
                let scrollInterval = setInterval(() => {
                    element.scrollBy(0, step);
                    findAndHighlightElements(0, null, levelOrders); // Detection during scroll
                    if (element.scrollTop === lastScrollTop) {
                        clearInterval(scrollInterval);
                        callback();
                    } else {
                        lastScrollTop = element.scrollTop;
                    }
                }, 500);
            }

            function findLargestScrollContainer() {
                let containers = Array.from(document.querySelectorAll('*')).filter(el => {
                    return (el.scrollHeight > el.clientHeight) && getComputedStyle(el).overflowY === 'auto';
                });
                containers.sort((a, b) => b.scrollHeight - a.scrollHeight);
                return containers[0] || null;
            }

            const stepSize = window.innerHeight; // Change this value to alter the scroll step, currently set to one viewport height
            scrollElementIncrementally(window, stepSize, () => {
                const largestScrollContainer = findLargestScrollContainer();
                if (largestScrollContainer) {
                    scrollElementIncrementally(largestScrollContainer, stepSize, () => {});
                }
            });
            highlightAndStoreInputSets();
        })();
        """
        different_elements = []
        different_input_elements = []
        new_elements = []
        await page.evaluate(script)
        await asyncio.sleep(1)
        updated_elements = await page.evaluate("window.detected_elements")
        updated_input_elements = await page.evaluate("window.detected_input_elements")

        new_elements = [
            el for el in updated_input_elements if el["hash"] not in {el["hash"] for el in input_elements_from_crawler}
        ]

        if new_elements:
            input_elements_from_crawler.extend(new_elements)
            different_input_elements.extend(new_elements)

        different_elements_by_hash = [
            el for el in updated_elements if el["hash"] not in {el["hash"] for el in elements_from_crawler}
        ]

        if different_elements_by_hash:
            elements_from_crawler.extend(different_elements_by_hash)
            different_elements.extend(different_elements_by_hash)

        await asyncio.sleep(0.1)

        return elements_from_crawler, input_elements_from_crawler
