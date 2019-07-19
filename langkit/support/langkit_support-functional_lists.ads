private with Langkit_Support.Bump_Ptr;

--  This package defines a functional singly-linked list type. You can only
--  prepend elements at the beginning of the list. Iterating on the list is
--  done via the ``Head`` and ``Tail`` operations, that will return the head
--  and tail of the list.
--
--  Ultimately, the collection of functional lists form a tree that all
--  converge to the same 'Root', that is the last element in the list.
--
--  To create a list, you concat elements to the empty list. Here is an example
--  of use:
--
--  .. code:: ada
--
--     with Ada.Text_IO; use Ada.Text_IO;
--     with Langkit_Support.Functional_Lists;
--       procedure Main is
--          package Int_Lists
--          is new Langkit_Support.Functional_Lists (Integer);
--          use Int_Lists;
--
--          A : List := Create;
--          --  This list is init with Create, so will contain a pool.
--
--          B : List;
--          --  This one is just init to ``No_List``.
--          --  Careful! pools will be created
--          --  when concat-ing to that.
--
--          D : List := 1 & (2 & (3 & B));
--          --  This one contains a new pool.
--
--          E : List := 1 & (2 & (9 & No_List));
--          --  This one contains a new pool too.
--
--          ----------------
--          -- Print_List --
--          ----------------
--
--          procedure Print_List (S : List) is
--          begin
--             if not Has_Element (S) then
--                return;
--             else
--                Put_Line (Head (S)'Image);
--                Print_List (Tail (S));
--             end if;
--          end Print_List;
--       begin
--          Print_List (A);
--          Print_List (1 & (2 & (3 & A)));
--          Print_List (D);
--          Print_List (122 & Tail (Tail (D)));
--          Print_List (E);
--
--          Destroy (A);
--          Destroy (D);
--          Destroy (E);
--       end Main;

generic
   type T is private;
package Langkit_Support.Functional_Lists is
   type List is private
     with Iterable => (First => Iter_First,
                       Next  => Iter_Next,
                       Has_Element => Iter_Has_Element,
                       Element => Iter_Element);

   function Create return List;
   function "&" (L : T; R : List) return List;
   function Head (Self : List) return T;
   function Tail (Self : List) return List;
   procedure Destroy (Self : in out List);
   function Has_Element (Self : List) return Boolean;
   function Length (Self : List) return Natural;

   type T_Array is array (Positive range <>) of T;
   function To_Array (Self : List) return T_Array;

   No_List : constant List;

   --  Function used to implement Iterable aspect. Not meant for public
   --  consumption.

   function Iter_First (Self : List) return List is (Self);
   function Iter_Next (Dummy, Iter : List) return List is (Tail (Iter));
   function Iter_Has_Element (Dummy, Iter : List) return Boolean
   is (Has_Element (Iter));
   function Iter_Element (Dummy, Iter : List) return T is (Head (Iter));

private

   package Bump renames Langkit_Support.Bump_Ptr;

   type List_Node;
   type Node_Ptr is access all List_Node;

   type List_Node is record
      El : T;
      Next : Node_Ptr := null;
   end record;

   type List is record
      Pool : Bump.Bump_Ptr_Pool;
      First : Node_Ptr := null;
      Length : Natural := 0;
   end record;

   No_List : constant List := (Bump.No_Pool, null, 0);

end Langkit_Support.Functional_Lists;