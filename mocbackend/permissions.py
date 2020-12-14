from rest_framework import permissions


# Ako has_permission vrati False onda ne ulazi u has_object_permission

class IsStaffOrInAnyAllowedGroups(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            view.allowed_groups
        except AttributeError:
            return False
        return request.user and request.user.is_active and (
                request.user.is_staff or request.user.groups.filter(name__in=view.allowed_groups).exists())

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class IsSafeMethod(permissions.BasePermission):
    SAFE_METHODS = ('HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        return request.method in self.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class IsAllowedActions(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            return view.action in view.allowed_actions
        except AttributeError:
            return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)


class IsSelfOrIsAllowedActions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        try:
            if view.action in view.allowed_actions:
                return True
        except AttributeError:
            pass
        return request.user.is_active and request.user == obj


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_active and request.user == obj.owner.user


class IsStaffOrInImporterGroup(permissions.BasePermission):
    importer_groups = ['importer']

    def has_permission(self, request, view):
        return request.user.is_active and (
                request.user.is_staff or request.user.groups.filter(name__in=self.importer_groups).exists())

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request=request, view=view)
